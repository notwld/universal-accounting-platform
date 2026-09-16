import uuid

from django.utils.deprecation import MiddlewareMixin


class RequestIdMiddleware(MiddlewareMixin):
    header = "HTTP_X_REQUEST_ID"

    def process_request(self, request):
        request_id = request.META.get(self.header) or str(uuid.uuid4())
        request.request_id = request_id

    def process_response(self, request, response):
        response["X-Request-ID"] = getattr(request, "request_id", "")
        return response
