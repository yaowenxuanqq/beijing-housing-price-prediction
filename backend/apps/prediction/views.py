# -*- coding: utf-8 -*-
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ml.predictor import HousingPredictor

from .models import PredictionLog
from .serializers import PredictRequestSerializer


class PredictView(APIView):
    """单条房价预测：ratio × 当期区中位单价 → 单价/总价"""

    def post(self, request):
        ser = PredictRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"errors": ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        payload = ser.validated_data
        try:
            result = HousingPredictor.instance().predict(payload)
        except FileNotFoundError:
            return Response({"error": "模型文件不存在，请先运行 scripts/04_tune.py"},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as exc:  # pragma: no cover
            return Response({"error": f"推理失败: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        PredictionLog.objects.create(
            input_json={k: (str(v) if hasattr(v, "isoformat") else v) for k, v in payload.items()},
            predicted_ratio=result["ratio"],
            predicted_unit_price=result["predicted_unit_price"],
            predicted_total_price=result["predicted_total_price"],
            interval_low=result["interval_low"],
            interval_high=result["interval_high"],
            market_median_unit_price=result["market_median_unit_price"],
            model_version=result["model_version"],
        )
        return Response(result)
