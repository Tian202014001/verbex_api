import logging

from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ApiResponseMixin:
    def _json_response(self, success, message, data=None, meta=None, status=200, errors=None):
        payload = {
            "success": success,
            "message": message,
            "status": status,
        }
        if data is not None:
            payload["data"] = data
        if meta is not None:
            payload["meta"] = meta
        if errors is not None:
            payload["errors"] = errors
        return payload

    def _success(self, message, data=None, meta=None, status=200):
        return self._json_response(True, message, data=data, meta=meta, status=status)

    def _error(self, message, status=400, errors=None):
        return self._json_response(False, message, status=status, errors=errors)

    def _handle_exception(self, exc):
        if isinstance(exc, BadRequest):
            return self._error(str(exc.description), status=400)
        if isinstance(exc, MissingError):
            return self._error("Record not found.", status=404)
        if isinstance(exc, AccessError):
            return self._error("You do not have permission to perform this action.", status=403)
        if isinstance(exc, (ValidationError, UserError)):
            return self._error(str(exc), status=422)

        _logger.exception("Unexpected API error")
        return self._error("An unexpected server error occurred.", status=500)


class BaseApiController(http.Controller, ApiResponseMixin):
    def _get_product_model(self):
        return request.env["product.product"].sudo()

    def _get_sale_order_model(self):
        return request.env["sale.order"].sudo()

    def _parse_int_param(self, name, default, minimum=None, maximum=None):
        raw_value = request.params.get(name, default)
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise BadRequest(f"Invalid '{name}' value. Expected an integer.") from exc

        if minimum is not None and value < minimum:
            raise BadRequest(f"'{name}' must be greater than or equal to {minimum}.")
        if maximum is not None and value > maximum:
            raise BadRequest(f"'{name}' must be less than or equal to {maximum}.")
        return value

    def _parse_payload(self):
        payload = request.params or {}
        if not isinstance(payload, dict):
            raise BadRequest("Request body must be a JSON object.")
        return payload

    def _parse_bool_param(self, name):
        raw_value = request.params.get(name)
        if raw_value is None:
            return None

        normalized = str(raw_value).strip().lower()
        if normalized not in {"true", "false", "1", "0"}:
            raise BadRequest(f"Invalid '{name}' value. Use true or false.")
        return normalized in {"true", "1"}

    def _parse_optional_int_param(self, name, minimum=None):
        raw_value = request.params.get(name)
        if raw_value in (None, ""):
            return None

        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise BadRequest(f"Invalid '{name}' value. Expected an integer.") from exc

        if minimum is not None and value < minimum:
            raise BadRequest(f"'{name}' must be greater than or equal to {minimum}.")
        return value
