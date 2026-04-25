from math import ceil

from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.osv import expression

from .base_api import BaseApiController


class ProductApiController(BaseApiController):
    _allowed_write_fields = {
        "name",
        "default_code",
        "barcode",
        "list_price",
        "standard_price",
        "type",
        "categ_id",
        "active",
        "sale_ok",
        "purchase_ok",
        "description_sale",
        "description_purchase",
        "weight",
        "volume",
    }

    def _prepare_write_values(self, payload, partial=False):
        unknown_fields = sorted(set(payload) - self._allowed_write_fields)
        if unknown_fields:
            raise BadRequest(
                "Unsupported fields in payload: %s." % ", ".join(unknown_fields)
            )

        if not partial and "name" not in payload:
            raise BadRequest("Missing required field: name.")

        values = {}
        for field_name, field_value in payload.items():
            if field_name == "categ_id":
                if field_value in (None, False):
                    raise BadRequest("Field 'categ_id' cannot be empty.")
                try:
                    category_id = int(field_value)
                except (TypeError, ValueError) as exc:
                    raise BadRequest("Field 'categ_id' must be an integer.") from exc
                category = request.env["product.category"].sudo().browse(category_id).exists()
                if not category:
                    raise BadRequest("Invalid 'categ_id'. Category not found.")
                values[field_name] = category_id
                continue

            values[field_name] = field_value

        return values

    def _serialize_product(self, product):
        return {
            "id": product.id,
            "name": product.name,
            "default_code": product.default_code,
            "barcode": product.barcode,
            "list_price": product.list_price,
            "standard_price": product.standard_price,
            "type": product.type,
            "active": product.active,
            "sale_ok": product.sale_ok,
            "purchase_ok": product.purchase_ok,
            "categ_id": product.categ_id.id,
            "categ_name": product.categ_id.display_name,
            "uom_id": product.uom_id.id,
            "uom_name": product.uom_id.display_name,
            "description_sale": product.description_sale,
            "description_purchase": product.description_purchase,
            "weight": product.weight,
            "volume": product.volume,
            "create_date": product.create_date.isoformat() if product.create_date else None,
            "write_date": product.write_date.isoformat() if product.write_date else None,
        }

    def _build_search_domain(self, search_term, params=None):
        domain = []
        if search_term:
            domain = expression.OR([
                [("name", "ilike", search_term)],
                [("default_code", "ilike", search_term)],
                [("barcode", "ilike", search_term)],
            ])

        active_filter = self._parse_bool_param("active", params=params)
        if active_filter is not None:
            domain = expression.AND([domain, [("active", "=", active_filter)]])

        return domain, active_filter

    def _build_product_search_domain(self, params=None):
        params = params if params is not None else request.params
        name = (params.get("name") or "").strip()
        if not name:
            raise BadRequest("Field 'name' is required for product search.")

        exact_match = self._parse_bool_param("exact_match", params=params)
        operator = "=" if exact_match else "ilike"
        domain = [[("name", operator, name)]]

        default_code = (params.get("default_code") or "").strip()
        if default_code:
            domain.append([("default_code", "ilike", default_code)])

        barcode = (params.get("barcode") or "").strip()
        if barcode:
            domain.append([("barcode", "ilike", barcode)])

        product_type = (params.get("type") or "").strip()
        if product_type:
            domain.append([("type", "=", product_type)])

        categ_id = self._parse_optional_int_param("categ_id", minimum=1, params=params)
        if categ_id is not None:
            category = request.env["product.category"].sudo().browse(categ_id).exists()
            if not category:
                raise BadRequest("Invalid 'categ_id'. Category not found.")
            domain.append([("categ_id", "=", categ_id)])

        for field_name in ("active", "sale_ok", "purchase_ok"):
            field_value = self._parse_bool_param(field_name, params=params)
            if field_value is not None:
                domain.append([(field_name, "=", field_value)])

        return expression.AND(domain), name

    def _parse_http_json_payload(self):
        payload = request.httprequest.get_json(silent=True)
        if payload is None:
            payload = request.params or {}
        if not isinstance(payload, dict):
            raise BadRequest("Request body must be a JSON object.")
        return payload

    def _search_products_from_params(self, params):
        page = self._parse_int_param("page", 1, minimum=1, params=params)
        page_size = self._parse_int_param("page_size", 20, minimum=1, maximum=100, params=params)
        domain, name = self._build_product_search_domain(params=params)

        product_model = self._get_product_model()
        if self._parse_bool_param("active", params=params) is False:
            product_model = product_model.with_context(active_test=False)

        total = product_model.search_count(domain)
        offset = (page - 1) * page_size
        products = product_model.search(domain, offset=offset, limit=page_size, order="id desc")

        meta = {
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": ceil(total / page_size) if total else 0,
            "has_next": offset + page_size < total,
            "has_previous": page > 1,
            "filters": {
                "name": name,
                "default_code": (params.get("default_code") or None),
                "barcode": (params.get("barcode") or None),
                "type": (params.get("type") or None),
                "categ_id": self._parse_optional_int_param("categ_id", minimum=1, params=params),
                "active": self._parse_bool_param("active", params=params),
                "sale_ok": self._parse_bool_param("sale_ok", params=params),
                "purchase_ok": self._parse_bool_param("purchase_ok", params=params),
                "exact_match": self._parse_bool_param("exact_match", params=params) or False,
            },
        }
        data = [self._serialize_product(product) for product in products]
        return self._success("Products searched successfully.", data=data, meta=meta)

    @http.route(
        "/api/v1/products/list",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
        readonly=True,
    )
    def list_products(self, **kwargs):
        try:
            page = self._parse_int_param("page", 1, minimum=1)
            page_size = self._parse_int_param("page_size", 20, minimum=1, maximum=100)
            search_term = (request.params.get("search") or "").strip()
            domain, active_filter = self._build_search_domain(search_term)

            product_model = self._get_product_model()
            if active_filter is False:
                product_model = product_model.with_context(active_test=False)
            total = product_model.search_count(domain)
            offset = (page - 1) * page_size
            products = product_model.search(domain, offset=offset, limit=page_size, order="id desc")

            meta = {
                "page": page,
                "page_size": page_size,
                "total_records": total,
                "total_pages": ceil(total / page_size) if total else 0,
                "has_next": offset + page_size < total,
                "has_previous": page > 1,
                "search": search_term or None,
            }
            data = [self._serialize_product(product) for product in products]
            return self._success("Products fetched successfully.", data=data, meta=meta)
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route(
        "/api/v1/products/search",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
        readonly=True,
    )
    def search_products(self, **kwargs):
        try:
            return self._search_products_from_params(request.params)
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route(
        "/api/v1/products/search/flat",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        readonly=True,
    )
    def search_products_flat(self, **kwargs):
        try:
            result = self._search_products_from_params(self._parse_http_json_payload())
            return request.make_json_response(result, status=result["status"])
        except Exception as exc:
            error = self._handle_exception(exc)
            return request.make_json_response(error, status=error["status"])

    @http.route(
        "/api/v1/products/get/<int:product_id>",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
        readonly=True,
    )
    def get_product(self, product_id, **kwargs):
        try:
            product = self._get_product_model().with_context(active_test=False).browse(product_id).exists()
            if not product:
                raise MissingError("Product not found.")
            return self._success("Product fetched successfully.", data=self._serialize_product(product))
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route(
        "/api/v1/products/create",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
    )
    def create_product(self, **kwargs):
        try:
            values = self._prepare_write_values(self._parse_payload(), partial=False)
            product = self._get_product_model().create(values)
            return self._success(
                "Product created successfully.",
                data=self._serialize_product(product),
                status=201,
            )
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route(
        "/api/v1/products/update/<int:product_id>",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
    )
    def update_product(self, product_id, **kwargs):
        try:
            payload = self._parse_payload()
            if not payload:
                raise BadRequest("Request body cannot be empty.")

            product = self._get_product_model().with_context(active_test=False).browse(product_id).exists()
            if not product:
                raise MissingError("Product not found.")

            values = self._prepare_write_values(payload, partial=True)
            product.write(values)
            return self._success("Product updated successfully.", data=self._serialize_product(product))
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route(
        "/api/v1/products/delete/<int:product_id>",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
    )
    def delete_product(self, product_id, **kwargs):
        try:
            product = self._get_product_model().with_context(active_test=False).browse(product_id).exists()
            if not product:
                raise MissingError("Product not found.")

            product.unlink()
            return self._success("Product deleted successfully.", data={"id": product_id})
        except Exception as exc:
            return self._handle_exception(exc)
