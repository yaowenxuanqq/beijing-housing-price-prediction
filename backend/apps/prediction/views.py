# -*- coding: utf-8 -*-
import csv
import logging
import time
import uuid
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
from .serializers import PredictRequestSerializer, PredictionLogSerializer

logger = logging.getLogger(__name__)


def _safe_input(payload):
    return {
        k: (str(v) if hasattr(v, "isoformat") else v)
        for k, v in payload.items()
    }


def _log_prediction(request_id, payload, result, duration_ms, response_json):
    PredictionLog.objects.create(
        request_id=request_id,
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


def _predict_response(request, explain=False):
    ser = PredictRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response({"errors": ser.errors}, status=status.HTTP_400_BAD_REQUEST)

    payload = dict(ser.validated_data)
    request_id = uuid.uuid4()
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
    _log_prediction(request_id, payload, result, duration_ms, response_json)
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


class PredictionHistoryView(generics.ListAPIView):
    serializer_class = PredictionLogSerializer

    def get_queryset(self):
        qs = PredictionLog.objects.all().order_by("-created_at", "-id")
        version = self.request.query_params.get("model_version")
        if version:
            qs = qs.filter(model_version=version)
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
            "request_id", "created_at", "district_name", "square", "rooms",
            "predicted_unit_price", "predicted_total_price", "interval_low",
            "interval_high", "interval_method", "model_version", "duration_ms",
        ])
        for log in logs.iterator():
            data = log.input_json or {}
            writer.writerow([
                log.request_id, log.created_at, data.get("district_name", ""),
                data.get("square", ""), data.get("rooms", ""),
                log.predicted_unit_price, log.predicted_total_price,
                log.interval_low, log.interval_high, log.interval_method,
                log.model_version, log.duration_ms,
            ])
        return response


class CurrentModelView(APIView):
    """部署模型的状态、产物身份和近期运行统计。"""

    def get(self, request):
        try:
            predictor = HousingPredictor.instance()
            metadata = predictor.metadata()
            model_ready = True
        except Exception as exc:
            logger.exception("load model metadata failed")
            metadata = {"model_version": None, "model_file": None}
            model_ready = False
            error = str(exc)
        else:
            error = None

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        stats = PredictionLog.objects.aggregate(
            prediction_count=Count("id"),
            avg_duration_ms=Avg("duration_ms"),
            last_prediction_at=Max("created_at"),
        )
        stats["prediction_count_7d"] = PredictionLog.objects.filter(created_at__gte=week_ago).count()
        return Response({
            "ready": model_ready,
            "error": error,
            "model": metadata,
            "runtime": stats,
            "checked_at": now,
        })
