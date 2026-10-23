# -*- coding: utf-8 -*-
import csv
import io
import logging
import time
import uuid
from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Max
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ml.predictor import HousingPredictor

from .models import PredictionLog
from .serializers import (
    PredictRequestSerializer,
    PredictionLogSerializer,
    ScenarioRequestSerializer,
)

logger = logging.getLogger(__name__)

MAX_BATCH_ROWS = 200
MAX_BATCH_BYTES = 5 * 1024 * 1024
BOOL_FIELDS = {"elevator", "subway", "five_years"}


def _safe_input(payload):
    return {
        k: (str(v) if hasattr(v, "isoformat") else v)
        for k, v in payload.items()
    }


def _log_prediction(request_id, payload, result, duration_ms, response_json,
                    source="single", batch_id=None):
    PredictionLog.objects.create(
        request_id=request_id,
        source=source,
        batch_id=batch_id,
        input_json=_safe_input(payload),
        predicted_ratio=result.get("ratio"),
        predicted_unit_price=result.get("predicted_unit_price"),
        predicted_total_price=result.get("predicted_total_price"),
        interval_low=result.get("interval_low"),
        interval_high=result.get("interval_high"),
        interval_method=result.get("interval_method", ""),
        market_median_unit_price=result.get("market_median_unit_price"),
        model_version=result.get("model_version", ""),
        duration_ms=round(duration_ms, 2),
        response_json=response_json,
    )


def _log_best_effort(*args, **kwargs):
    try:
        _log_prediction(*args, **kwargs)
    except Exception:
        logger.exception("prediction log failed")


def _predict_response(request, explain=False):
    ser = PredictRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response({"errors": ser.errors}, status=status.HTTP_400_BAD_REQUEST)

    payload = dict(ser.validated_data)
    request_id = uuid.uuid4()
    source = "explain" if explain else "single"
    started = time.perf_counter()
    try:
        predictor = HousingPredictor.instance()
        if explain:
            explained = predictor.explain(payload)
            result = explained["prediction"]
            response_json = explained
        else:
            result = predictor.predict(payload)
            response_json = result
    except FileNotFoundError:
        return Response(
            {"error": "模型文件不存在，请检查部署配置", "request_id": str(request_id)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception:
        logger.exception("prediction failed request_id=%s", request_id)
        return Response(
            {"error": "预测服务暂时不可用，请稍后重试", "request_id": str(request_id)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    duration_ms = (time.perf_counter() - started) * 1000
    _log_best_effort(request_id, payload, result, duration_ms, response_json, source=source)
    response = dict(result)
    response["request_id"] = str(request_id)
    if explain:
        response["explanation"] = explained["explanation"]
    return Response(response)


class PredictView(APIView):
    """单条房价预测：ratio × 当期区中位单价 → 单价/总价"""

    def post(self, request):
        return _predict_response(request, explain=False)


class PredictExplanationView(APIView):
    """单条房价预测 + TreeSHAP 局部解释。"""

    def post(self, request):
        return _predict_response(request, explain=True)


class ScenarioPredictView(APIView):
    """给定基础房源和若干改动，输出多个敏感性/情景方案。"""

    def post(self, request):
        request_ser = ScenarioRequestSerializer(data=request.data)
        if not request_ser.is_valid():
            return Response({"errors": request_ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        base_ser = PredictRequestSerializer(data=request_ser.validated_data["base"])
        if not base_ser.is_valid():
            return Response({"errors": {"base": base_ser.errors}}, status=status.HTTP_400_BAD_REQUEST)

        base_payload = dict(base_ser.validated_data)
        allowed_fields = set(PredictRequestSerializer().fields.keys())
        prepared = []
        for index, item in enumerate(request_ser.validated_data["scenarios"]):
            changes = dict(item.get("changes") or {})
            unknown = sorted(set(changes) - allowed_fields)
            if unknown:
                return Response(
                    {"errors": {f"scenarios.{index}.changes": f"不支持字段：{', '.join(unknown)}"}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            scenario_ser = PredictRequestSerializer(data={**base_payload, **changes})
            if not scenario_ser.is_valid():
                return Response(
                    {"errors": {f"scenarios.{index}": scenario_ser.errors}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            prepared.append((item["name"], changes, dict(scenario_ser.validated_data)))

        try:
            predictor = HousingPredictor.instance()
        except FileNotFoundError:
            return Response({"error": "模型文件不存在，请检查部署配置"}, status=503)
        except Exception:
            logger.exception("scenario model load failed")
            return Response({"error": "预测服务暂时不可用，请稍后重试"}, status=500)

        group_id = uuid.uuid4()
        started = time.perf_counter()
        try:
            baseline = predictor.predict(base_payload)
        except Exception:
            logger.exception("scenario baseline failed")
            return Response({"error": "预测服务暂时不可用，请稍后重试"}, status=500)
        baseline_duration = (time.perf_counter() - started) * 1000
        baseline_id = uuid.uuid4()
        _log_best_effort(
            baseline_id, base_payload, baseline, baseline_duration, baseline,
            source="scenario", batch_id=group_id,
        )
        baseline_response = {
            "name": "当前方案",
            "request_id": str(baseline_id),
            "changes": {},
            **baseline,
        }

        scenario_rows = []
        for name, changes, payload in prepared:
            started = time.perf_counter()
            try:
                result = predictor.predict(payload)
            except Exception:
                logger.exception("scenario prediction failed name=%s", name)
                return Response({"error": "预测服务暂时不可用，请稍后重试"}, status=500)
            duration_ms = (time.perf_counter() - started) * 1000
            request_id = uuid.uuid4()
            _log_best_effort(
                request_id, payload, result, duration_ms, result,
                source="scenario", batch_id=group_id,
            )
            delta_unit = result["predicted_unit_price"] - baseline["predicted_unit_price"]
            delta_total = result["predicted_total_price"] - baseline["predicted_total_price"]
            base_total = baseline["predicted_total_price"] or 1
            scenario_rows.append({
                "name": name,
                "request_id": str(request_id),
                "changes": changes,
                **result,
                "delta_unit_price": round(delta_unit, 1),
                "delta_total_price": round(delta_total, 1),
                "delta_pct": round(delta_total / base_total * 100, 2),
            })

        return Response({
            "batch_id": str(group_id),
            "baseline": baseline_response,
            "scenarios": scenario_rows,
            "note": "情景对比反映模型敏感性，不是因果推断；改动必须符合实际业务条件。",
        })


def _normalize_batch_row(row):
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        key = key.strip()
        if not key or value is None:
            continue
        value = value.strip()
        if not value:
            continue
        if key in BOOL_FIELDS:
            lowered = value.lower()
            if lowered in {"1", "true", "yes", "y", "是", "有"}:
                value = True
            elif lowered in {"0", "false", "no", "n", "否", "无"}:
                value = False
        normalized[key] = value
    return normalized


def _batch_template_response():
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="batch_prediction_template.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "district_name", "square", "rooms", "halls", "bathrooms",
        "floor_position", "total_floors", "house_age", "renovation",
        "building_type", "building_structure", "ladder_ratio",
        "elevator", "subway", "five_years", "market_median_unit_price",
    ])
    writer.writerow([
        "朝阳区", "89.5", "2", "1", "1", "中", "18", "12", "3",
        "1", "2", "2", "true", "true", "true", "66421",
    ])
    return response


class BatchPredictView(APIView):
    """CSV 批量估价，限额 200 行，同步处理，避免引入无必要的异步队列。"""

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"error": "请上传 CSV 文件"}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_BATCH_BYTES:
            return Response({"error": "文件不能超过 5 MB"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            text = upload.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            headers = [h.strip() for h in (reader.fieldnames or [])]
            rows = [row for row in reader if any((v or "").strip() for v in row.values())]
        except (UnicodeDecodeError, csv.Error):
            return Response({"error": "CSV 必须为 UTF-8 编码"}, status=status.HTTP_400_BAD_REQUEST)

        required = {"district_name", "square", "market_median_unit_price"}
        missing = sorted(required - set(headers))
        if missing:
            return Response(
                {"error": f"缺少必填列：{', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(rows) > MAX_BATCH_ROWS:
            return Response(
                {"error": f"单次最多 {MAX_BATCH_ROWS} 行，当前 {len(rows)} 行"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not rows:
            return Response({"error": "CSV 没有可处理的数据行"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            predictor = HousingPredictor.instance()
        except FileNotFoundError:
            return Response({"error": "模型文件不存在，请检查部署配置"}, status=503)
        except Exception:
            logger.exception("batch model load failed")
            return Response({"error": "预测服务暂时不可用，请稍后重试"}, status=500)

        batch_id = uuid.uuid4()
        results = []
        errors = []
        for row_number, raw_row in enumerate(rows, start=2):
            payload = _normalize_batch_row(raw_row)
            ser = PredictRequestSerializer(data=payload)
            if not ser.is_valid():
                errors.append({"row": row_number, "errors": ser.errors})
                continue
            payload = dict(ser.validated_data)
            started = time.perf_counter()
            try:
                result = predictor.predict(payload)
            except Exception:
                logger.exception("batch row prediction failed row=%s", row_number)
                errors.append({"row": row_number, "errors": "推理失败"})
                continue
            duration_ms = (time.perf_counter() - started) * 1000
            request_id = uuid.uuid4()
            _log_best_effort(
                request_id, payload, result, duration_ms, result,
                source="batch", batch_id=batch_id,
            )
            results.append({
                "row": row_number,
                "request_id": str(request_id),
                "input_json": _safe_input(payload),
                **result,
            })

        return Response({
            "batch_id": str(batch_id),
            "total": len(rows),
            "success": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        })


class BatchTemplateView(APIView):
    def get(self, request):
        return _batch_template_response()


class PredictionHistoryView(generics.ListAPIView):
    serializer_class = PredictionLogSerializer

    def get_queryset(self):
        qs = PredictionLog.objects.all().order_by("-created_at", "-id")
        version = self.request.query_params.get("model_version")
        if version:
            qs = qs.filter(model_version=version)
        source = self.request.query_params.get("source")
        if source:
            qs = qs.filter(source=source)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            parsed = parse_date(date_from)
            if not parsed:
                raise ValidationError({"date_from": "日期格式必须为 YYYY-MM-DD"})
            qs = qs.filter(created_at__date__gte=parsed)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            parsed = parse_date(date_to)
            if not parsed:
                raise ValidationError({"date_to": "日期格式必须为 YYYY-MM-DD"})
            qs = qs.filter(created_at__date__lte=parsed)
        return qs


class PredictionHistoryDetailView(generics.RetrieveAPIView):
    queryset = PredictionLog.objects.all()
    serializer_class = PredictionLogSerializer


class PredictionExportView(APIView):
    """导出预测记录，便于论文附录或答辩展示。"""

    def get(self, request):
        qs = PredictionHistoryView()
        qs.request = request
        logs = qs.get_queryset()
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="prediction_history.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "request_id", "batch_id", "source", "created_at", "district_name",
            "square", "rooms", "predicted_unit_price", "predicted_total_price",
            "interval_low", "interval_high", "interval_method", "model_version",
            "duration_ms",
        ])
        for log in logs.iterator():
            data = log.input_json or {}
            writer.writerow([
                log.request_id, log.batch_id or "", log.source, log.created_at,
                data.get("district_name", ""), data.get("square", ""),
                data.get("rooms", ""), log.predicted_unit_price,
                log.predicted_total_price, log.interval_low, log.interval_high,
                log.interval_method, log.model_version, log.duration_ms,
            ])
        return response


def _percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _runtime_stats(now):
    week_ago = now - timedelta(days=7)
    stats = PredictionLog.objects.aggregate(
        prediction_count=Count("id"),
        avg_duration_ms=Avg("duration_ms"),
        last_prediction_at=Max("created_at"),
    )
    recent = list(
        PredictionLog.objects.filter(created_at__gte=week_ago)
        .values("created_at", "duration_ms", "source")
    )
    stats["prediction_count_7d"] = len(recent)
    durations = [row["duration_ms"] for row in recent if row["duration_ms"] is not None]
    stats["latency_p50_ms"] = round(_percentile(durations, 0.50), 1) if durations else None
    stats["latency_p95_ms"] = round(_percentile(durations, 0.95), 1) if durations else None
    stats["source_counts"] = {
        row["source"]: row["count"]
        for row in PredictionLog.objects.values("source").annotate(count=Count("id"))
    }
    by_day = defaultdict(list)
    for row in recent:
        by_day[row["created_at"].date()].append(row)
    stats["recent_daily"] = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        rows = by_day.get(day, [])
        day_durations = [r["duration_ms"] for r in rows if r["duration_ms"] is not None]
        stats["recent_daily"].append({
            "date": day.isoformat(),
            "count": len(rows),
            "avg_duration_ms": round(sum(day_durations) / len(day_durations), 1) if day_durations else None,
        })
    return stats


class CurrentModelView(APIView):
    """部署模型的状态、产物身份和近期运行统计。"""

    def get(self, request):
        try:
            predictor = HousingPredictor.instance()
            metadata = predictor.metadata()
            model_ready = True
        except Exception:
            logger.exception("load model metadata failed")
            metadata = {"model_version": None, "model_file": None}
            model_ready = False
            error = "model unavailable"
        else:
            error = None

        now = timezone.now()
        return Response({
            "ready": model_ready,
            "error": error,
            "model": metadata,
            "runtime": _runtime_stats(now),
            "checked_at": now,
        })
