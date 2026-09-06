-- ChannelForge ERP schema for Supabase / PostgreSQL
-- Apply in the SQL editor, then point DATABASE_URL at postgresql+asyncpg://...

create extension if not exists "pgcrypto";

create table if not exists tenants (
  id serial primary key,
  name varchar(200) unique not null,
  slug varchar(80) unique not null,
  timezone varchar(64) default 'UTC',
  currency varchar(8) default 'USD',
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists users (
  id serial primary key,
  tenant_id int references tenants(id),
  email varchar(255) unique not null,
  full_name varchar(200) not null,
  hashed_password varchar(255) not null,
  role varchar(32) default 'viewer',
  is_active boolean default true,
  last_login_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists audit_logs (
  id serial primary key,
  tenant_id int references tenants(id),
  user_id int references users(id),
  action varchar(80),
  entity_type varchar(80),
  entity_id varchar(80) default '',
  payload text default '{}',
  ip_address varchar(64),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists channels (
  id serial primary key,
  tenant_id int references tenants(id),
  code varchar(40),
  name varchar(120),
  marketplace varchar(40),
  region varchar(16) default 'US',
  status varchar(24) default 'connected',
  sync_mode varchar(24) default 'webhook_plus_poll',
  last_synced_at timestamptz,
  rate_limit_rpm int default 60,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists channel_credentials (
  id serial primary key,
  channel_id int references channels(id),
  key_name varchar(80),
  encrypted_value text,
  expires_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists webhook_inbox (
  id serial primary key,
  tenant_id int references tenants(id),
  channel_id int references channels(id),
  marketplace varchar(40),
  event_type varchar(80),
  payload text,
  signature varchar(255) default '',
  processed boolean default false,
  processed_at timestamptz,
  error text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists products (
  id serial primary key,
  tenant_id int references tenants(id),
  sku varchar(80),
  title varchar(500),
  description text default '',
  brand varchar(120) default '',
  category varchar(200) default '',
  product_type varchar(32) default 'simple',
  status varchar(24) default 'active',
  cogs numeric(12,4) default 0,
  weight_g int default 0,
  hs_code varchar(32) default '',
  compliance_json text default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists product_variants (
  id serial primary key,
  product_id int references products(id),
  sku varchar(80),
  title varchar(300),
  option1 varchar(80) default '',
  option2 varchar(80) default '',
  option3 varchar(80) default '',
  barcode varchar(64) default '',
  cogs numeric(12,4) default 0,
  price numeric(12,4) default 0,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists product_images (
  id serial primary key,
  product_id int references products(id),
  url varchar(1000),
  alt varchar(255) default '',
  position int default 0,
  is_primary boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists bundle_items (
  id serial primary key,
  parent_product_id int references products(id),
  child_variant_id int references product_variants(id),
  quantity int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists listing_templates (
  id serial primary key,
  tenant_id int references tenants(id),
  name varchar(160),
  marketplace varchar(40),
  title_pattern varchar(500) default '{title}',
  description_pattern text default '{description}',
  price_rule varchar(80) default 'base',
  price_modifier numeric(8,4) default 0,
  attribute_map_json text default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists listings (
  id serial primary key,
  tenant_id int references tenants(id),
  product_id int references products(id),
  variant_id int references product_variants(id),
  channel_id int references channels(id),
  template_id int references listing_templates(id),
  external_id varchar(120) default '',
  title varchar(500),
  description text default '',
  price numeric(12,4) default 0,
  promo_price numeric(12,4),
  currency varchar(8) default 'USD',
  status varchar(24) default 'draft',
  quantity_pushed int default 0,
  category_external varchar(200) default '',
  attributes_json text default '{}',
  last_error text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists category_mappings (
  id serial primary key,
  tenant_id int references tenants(id),
  internal_category varchar(200),
  marketplace varchar(40),
  external_category_id varchar(120),
  external_category_name varchar(300) default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists warehouses (
  id serial primary key,
  tenant_id int references tenants(id),
  code varchar(32),
  name varchar(160),
  country varchar(8) default 'US',
  is_default boolean default false,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists inventory_balances (
  id serial primary key,
  tenant_id int references tenants(id),
  variant_id int references product_variants(id),
  warehouse_id int references warehouses(id),
  on_hand int default 0,
  reserved int default 0,
  inbound int default 0,
  safety_stock int default 0,
  version int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists inventory_movements (
  id serial primary key,
  tenant_id int references tenants(id),
  variant_id int references product_variants(id),
  warehouse_id int references warehouses(id),
  quantity_delta int not null,
  reason varchar(40),
  reference_type varchar(40) default '',
  reference_id varchar(80) default '',
  note text default '',
  unit_cost numeric(12,4) default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists sync_events (
  id serial primary key,
  tenant_id int references tenants(id),
  channel_id int references channels(id),
  direction varchar(16),
  entity_type varchar(40),
  entity_id varchar(80) default '',
  status varchar(24) default 'pending',
  conflict_policy varchar(32) default 'erp_wins',
  payload text default '{}',
  result text default '{}',
  error text,
  retry_count int default 0,
  next_retry_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists orders (
  id serial primary key,
  tenant_id int references tenants(id),
  channel_id int references channels(id),
  warehouse_id int references warehouses(id),
  external_id varchar(120),
  order_number varchar(80),
  status varchar(32) default 'pending',
  fulfillment_status varchar(32) default 'unfulfilled',
  financial_status varchar(32) default 'paid',
  currency varchar(8) default 'USD',
  subtotal numeric(12,4) default 0,
  shipping_charged numeric(12,4) default 0,
  tax numeric(12,4) default 0,
  discount numeric(12,4) default 0,
  total numeric(12,4) default 0,
  customer_name varchar(200) default '',
  customer_email varchar(255) default '',
  shipping_country varchar(8) default '',
  placed_at timestamptz,
  shipped_at timestamptz,
  raw_payload text default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists order_items (
  id serial primary key,
  order_id int references orders(id),
  variant_id int references product_variants(id),
  sku varchar(80),
  title varchar(400),
  quantity int default 1,
  unit_price numeric(12,4) default 0,
  cogs_at_sale numeric(12,4) default 0,
  marketplace_fee numeric(12,4) default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists return_requests (
  id serial primary key,
  tenant_id int references tenants(id),
  order_id int references orders(id),
  channel_id int references channels(id),
  rma_number varchar(80) unique,
  status varchar(32) default 'requested',
  reason_code varchar(64) default 'other',
  reason_text text default '',
  ai_category varchar(64) default '',
  suggested_resolution varchar(80) default '',
  refund_amount numeric(12,4) default 0,
  restock boolean default false,
  approved_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists return_items (
  id serial primary key,
  return_id int references return_requests(id),
  order_item_id int references order_items(id),
  sku varchar(80),
  quantity int default 1,
  condition varchar(32) default 'unopened',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists order_costs (
  id serial primary key,
  tenant_id int references tenants(id),
  order_id int references orders(id),
  cost_type varchar(40),
  amount numeric(12,4) default 0,
  currency varchar(8) default 'USD',
  source varchar(40) default 'system',
  note text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists payouts (
  id serial primary key,
  tenant_id int references tenants(id),
  channel_id int references channels(id),
  external_id varchar(120),
  amount numeric(12,4) default 0,
  currency varchar(8) default 'USD',
  status varchar(24) default 'pending',
  paid_at timestamptz,
  expected_amount numeric(12,4) default 0,
  fee_total numeric(12,4) default 0,
  raw_payload text default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists payout_matches (
  id serial primary key,
  payout_id int references payouts(id),
  order_id int references orders(id),
  matched_amount numeric(12,4) default 0,
  match_confidence numeric(5,4) default 1,
  method varchar(32) default 'auto',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists discrepancies (
  id serial primary key,
  tenant_id int references tenants(id),
  channel_id int references channels(id),
  order_id int references orders(id),
  payout_id int references payouts(id),
  kind varchar(40),
  severity varchar(16) default 'medium',
  amount numeric(12,4) default 0,
  description text default '',
  suggested_action text default '',
  status varchar(24) default 'open',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists gross_profit_snapshots (
  id serial primary key,
  tenant_id int references tenants(id),
  order_id int references orders(id),
  sku varchar(80) default '',
  channel_code varchar(40) default '',
  selling_price numeric(12,4) default 0,
  cogs numeric(12,4) default 0,
  marketplace_fees numeric(12,4) default 0,
  shipping_cost numeric(12,4) default 0,
  returns_refunds numeric(12,4) default 0,
  ads numeric(12,4) default 0,
  gross_profit numeric(12,4) default 0,
  margin_pct numeric(8,4) default 0,
  formula text default '',
  period varchar(16) default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists accounting_connections (
  id serial primary key,
  tenant_id int references tenants(id),
  provider varchar(40),
  name varchar(120),
  status varchar(24) default 'connected',
  encrypted_credentials text default '',
  last_synced_at timestamptz,
  chart_of_accounts_json text default '[]',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists mapping_rules (
  id serial primary key,
  tenant_id int references tenants(id),
  connection_id int references accounting_connections(id),
  source_type varchar(40),
  source_code varchar(80),
  target_account varchar(80),
  target_account_name varchar(200) default '',
  tax_code varchar(40) default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists journal_entries (
  id serial primary key,
  tenant_id int references tenants(id),
  connection_id int references accounting_connections(id),
  external_id varchar(120) default '',
  entry_date timestamptz,
  memo varchar(400) default '',
  debit_account varchar(80),
  credit_account varchar(80),
  amount numeric(12,4) default 0,
  source_type varchar(40) default '',
  source_id varchar(80) default '',
  status varchar(24) default 'draft',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists ai_automation_logs (
  id serial primary key,
  tenant_id int references tenants(id),
  job_type varchar(48),
  trigger varchar(32) default 'user',
  actor varchar(160) default 'system',
  status varchar(24) default 'success',
  summary varchar(400) default '',
  entity_type varchar(40) default '',
  entity_id varchar(80) default '',
  model varchar(80) default 'heuristic',
  tokens_used int default 0,
  duration_ms int default 0,
  input_json text default '{}',
  output_json text default '{}',
  error text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_ai_logs_tenant on ai_automation_logs(tenant_id);
create index if not exists idx_ai_logs_type on ai_automation_logs(job_type);

create table if not exists ai_jobs (
  id serial primary key,
  tenant_id int references tenants(id),
  job_type varchar(40),
  status varchar(24) default 'queued',
  input_json text default '{}',
  output_json text default '{}',
  tokens_used int default 0,
  error text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists forecasts (
  id serial primary key,
  tenant_id int references tenants(id),
  variant_id int references product_variants(id),
  warehouse_id int references warehouses(id),
  horizon_days int default 30,
  predicted_demand int default 0,
  suggested_replenish int default 0,
  seasonality_index numeric(8,4) default 1,
  method varchar(40) default 'holt_winters_lite',
  confidence numeric(5,4) default 0.7,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists listing_suggestions (
  id serial primary key,
  tenant_id int references tenants(id),
  listing_id int references listings(id),
  field_name varchar(40),
  current_value text default '',
  suggested_value text default '',
  rationale text default '',
  accepted boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists anomaly_alerts (
  id serial primary key,
  tenant_id int references tenants(id),
  kind varchar(40),
  severity varchar(16) default 'medium',
  title varchar(200),
  detail text default '',
  entity_type varchar(40) default '',
  entity_id varchar(80) default '',
  status varchar(24) default 'open',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_orders_tenant on orders(tenant_id);
create index if not exists idx_listings_tenant on listings(tenant_id);
create index if not exists idx_balances_tenant on inventory_balances(tenant_id);
create index if not exists idx_sync_tenant on sync_events(tenant_id);
