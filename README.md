# verbex_api

This repository now contains an Odoo addon at `odoo_api` that exposes a JSON API for `product.product`.

Routes:
- `POST /api/v1/products/list`
- `POST /api/v1/products/search`
- `POST /api/v1/products/get/<product_id>`
- `POST /api/v1/products/create`
- `POST /api/v1/products/update/<product_id>`
- `POST /api/v1/products/delete/<product_id>`
- `POST /api/v1/sale-orders/create`

Notes:
- Authentication currently uses Odoo `auth="public"` and `type="json"`.
- Replace `auth="public"` with `auth="bearer"` later when token-based access is ready.
- The controller currently uses `sudo()` so public requests can read and modify products. Treat this as temporary.
- Requests should use Odoo JSON-RPC format with payload under `params`.
- Example list body: `{"jsonrpc":"2.0","method":"call","params":{"page":1,"page_size":20,"search":"desk"}}`
- Search body: `{"jsonrpc":"2.0","method":"call","params":{"name":"desk","default_code":"SKU","barcode":"123","type":"consu","categ_id":4,"active":true,"sale_ok":true,"purchase_ok":false,"exact_match":false,"page":1,"page_size":20}}`
- Sale order create body: `{"jsonrpc":"2.0","method":"call","params":{"partner_id":7,"client_order_ref":"WEB-1001","note":"Created from API","order_lines":[{"product_id":12,"product_uom_qty":2,"price_unit":1500},{"product_id":18,"product_uom_qty":1,"discount":5}]}}`
- Search API requires `name` and supports optional `default_code`, `barcode`, `type`, `categ_id`, `active`, `sale_ok`, `purchase_ok`, `exact_match`, `page`, and `page_size`.
- Sale order create requires `partner_id` and a non-empty `order_lines` list. Each line requires `product_id` and `product_uom_qty`. Optional order fields: `pricelist_id`, `warehouse_id`, `user_id`, `payment_term_id`, `client_order_ref`, `note`, `origin`. Optional line fields: `name`, `price_unit`, `product_uom`, `discount`.
- List responses include pagination metadata.
- Error responses are returned in a consistent JSON structure.
- Supported write fields: `name`, `default_code`, `barcode`, `list_price`, `standard_price`, `type`, `categ_id`, `active`, `sale_ok`, `purchase_ok`, `description_sale`, `description_purchase`, `weight`, `volume`.
