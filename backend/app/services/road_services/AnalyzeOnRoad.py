import os
from app.services.road_services.AnalyzeOnRoadBase import AnalyzeOnRoadBase
from app.core.config import settings_metric_transport

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


class AnalyzeOnRoad(AnalyzeOnRoadBase):

    def __init__(
        self,
        path_video=None,
        meter_per_pixel=None,
        region=None,
        model_path=settings_metric_transport.MODELS_PATH,
        time_step=30,
        is_draw=True,
        device=settings_metric_transport.DEVICE,
        iou=0.3,
        conf=0.2,
        show=False
    ):

        # Nếu không truyền từ API → dùng config
        if path_video is None:
            path_video = settings_metric_transport.PATH_VIDEOS[0]

        if meter_per_pixel is None:
            meter_per_pixel = settings_metric_transport.METER_PER_PIXELS[0]

        if region is None:
            region = settings_metric_transport.REGIONS[0]

        super().__init__(
            path_video=path_video,
            meter_per_pixel=meter_per_pixel,
            model_path=model_path,
            time_step=time_step,
            is_draw=is_draw,
            device=device,
            iou=iou,
            conf=conf,
            show=show,
            region=region
        )

    def update_for_frame(self):
        pass

    def update_for_vehicle(self):
        pass
