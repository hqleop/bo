from django.urls import re_path

from .consumers import TenderRealtimeConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/tenders/(?P<kind>procurement|sales)/(?P<tender_id>\d+)/$",
        TenderRealtimeConsumer.as_asgi(),
    ),
]
