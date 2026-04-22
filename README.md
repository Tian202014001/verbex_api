# verbex_api

This repository now contains an Odoo addon at `odoo_api` that exposes a JSON API for `product.product`.

Routes:
- `POST /api/v1/products/list`
- `POST /api/v1/products/search`
- `POST /api/v1/products/get/<product_id>`
- `POST /api/v1/products/create`
- `POST /api/v1/products/update/<product_id>`
- `POST /api/v1/products/delete/<product_id>`

Notes:
- Authentication currently uses Odoo `auth="public"` and `type="json"`.
- Replace `auth="public"` with `auth="bearer"` later when token-based access is ready.
- The controller currently uses `sudo()` so public requests can read and modify products. Treat this as temporary.
- Requests should use Odoo JSON-RPC format with payload under `params`.
- Example list body: `{"jsonrpc":"2.0","method":"call","params":{"page":1,"page_size":20,"search":"desk"}}`
- Search body: `{"jsonrpc":"2.0","method":"call","params":{"name":"desk","default_code":"SKU","barcode":"123","type":"consu","categ_id":4,"active":true,"sale_ok":true,"purchase_ok":false,"exact_match":false,"page":1,"page_size":20}}`
- Search API requires `name` and supports optional `default_code`, `barcode`, `type`, `categ_id`, `active`, `sale_ok`, `purchase_ok`, `exact_match`, `page`, and `page_size`.
- List responses include pagination metadata.
- Error responses are returned in a consistent JSON structure.
- Supported write fields: `name`, `default_code`, `barcode`, `list_price`, `standard_price`, `type`, `categ_id`, `active`, `sale_ok`, `purchase_ok`, `description_sale`, `description_purchase`, `weight`, `volume`.
