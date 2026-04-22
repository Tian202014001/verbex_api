from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request

from .base_api import BaseApiController


class SaleOrderApiController(BaseApiController):
    def _prepare_sale_order_values(self, payload):
        partner_id = payload.get("partner_id")
        if not partner_id:
            raise BadRequest("Field 'partner_id' is required.")
        try:
            partner_id = int(partner_id)
        except (TypeError, ValueError) as exc:
            raise BadRequest("Field 'partner_id' must be an integer.") from exc

        partner = request.env["res.partner"].sudo().browse(partner_id).exists()
        if not partner:
            raise BadRequest("Invalid 'partner_id'. Partner not found.")

        order_lines = payload.get("order_lines")
        if not isinstance(order_lines, list) or not order_lines:
            raise BadRequest("Field 'order_lines' is required and must be a non-empty list.")

        values = {
            "partner_id": partner_id,
        }

        optional_integer_fields = ("pricelist_id", "warehouse_id", "user_id", "payment_term_id")
        for field_name in optional_integer_fields:
            field_value = payload.get(field_name)
            if field_value in (None, ""):
                continue
            try:
                values[field_name] = int(field_value)
            except (TypeError, ValueError) as exc:
                raise BadRequest(f"Field '{field_name}' must be an integer.") from exc

        optional_simple_fields = ("client_order_ref", "note", "origin")
        for field_name in optional_simple_fields:
            if payload.get(field_name) not in (None, ""):
                values[field_name] = payload[field_name]

        line_commands = []
        for index, line in enumerate(order_lines, start=1):
            if not isinstance(line, dict):
                raise BadRequest(f"Each order line must be a JSON object. Invalid line at position {index}.")

            product_id = line.get("product_id")
            if not product_id:
                raise BadRequest(f"Field 'product_id' is required for order line {index}.")
            try:
                product_id = int(product_id)
            except (TypeError, ValueError) as exc:
                raise BadRequest(f"Field 'product_id' must be an integer for order line {index}.") from exc

            product = self._get_product_model().browse(product_id).exists()
            if not product:
                raise BadRequest(f"Invalid 'product_id' for order line {index}. Product not found.")

            quantity = line.get("product_uom_qty")
            if quantity in (None, ""):
                raise BadRequest(f"Field 'product_uom_qty' is required for order line {index}.")
            try:
                quantity = float(quantity)
            except (TypeError, ValueError) as exc:
                raise BadRequest(f"Field 'product_uom_qty' must be numeric for order line {index}.") from exc
            if quantity <= 0:
                raise BadRequest(f"Field 'product_uom_qty' must be greater than 0 for order line {index}.")

            line_vals = {
                "product_id": product_id,
                "product_uom_qty": quantity,
                "name": line.get("name") or product.display_name,
            }

            price_unit = line.get("price_unit")
            if price_unit not in (None, ""):
                try:
                    line_vals["price_unit"] = float(price_unit)
                except (TypeError, ValueError) as exc:
                    raise BadRequest(f"Field 'price_unit' must be numeric for order line {index}.") from exc

            if line.get("product_uom") not in (None, ""):
                try:
                    line_vals["product_uom"] = int(line["product_uom"])
                except (TypeError, ValueError) as exc:
                    raise BadRequest(f"Field 'product_uom' must be an integer for order line {index}.") from exc

            if line.get("discount") not in (None, ""):
                try:
                    line_vals["discount"] = float(line["discount"])
                except (TypeError, ValueError) as exc:
                    raise BadRequest(f"Field 'discount' must be numeric for order line {index}.") from exc

            line_commands.append((0, 0, line_vals))

        values["order_line"] = line_commands
        return values

    def _serialize_sale_order(self, order):
        return {
            "id": order.id,
            "name": order.name,
            "state": order.state,
            "partner_id": order.partner_id.id,
            "partner_name": order.partner_id.display_name,
            "date_order": order.date_order.isoformat() if order.date_order else None,
            "amount_untaxed": order.amount_untaxed,
            "amount_tax": order.amount_tax,
            "amount_total": order.amount_total,
            "currency_id": order.currency_id.id,
            "currency_name": order.currency_id.name,
            "client_order_ref": order.client_order_ref,
            "note": order.note,
            "order_lines": [
                {
                    "id": line.id,
                    "product_id": line.product_id.id,
                    "product_name": line.product_id.display_name,
                    "name": line.name,
                    "product_uom_qty": line.product_uom_qty,
                    "price_unit": line.price_unit,
                    "discount": line.discount,
                    "price_subtotal": line.price_subtotal,
                    "price_tax": line.price_tax,
                    "price_total": line.price_total,
                }
                for line in order.order_line
            ],
        }

    @http.route(
        "/api/v1/sale-orders/create",
        auth="public",
        type="json",
        methods=["POST"],
        csrf=False,
    )
    def create_sale_order(self, **kwargs):
        try:
            payload = self._parse_payload()
            values = self._prepare_sale_order_values(payload)
            order = self._get_sale_order_model().create(values)
            return self._success(
                "Sale order created successfully.",
                data=self._serialize_sale_order(order),
                status=201,
            )
        except Exception as exc:
            return self._handle_exception(exc)
