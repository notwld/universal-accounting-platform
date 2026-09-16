-- RLS policies for auth/tenancy tables (MD §49–50).
-- Apply on PostgreSQL only. App role must NOT have BYPASSRLS.
-- Session vars set by middleware: app.user_id, app.organization_id, app.location_id

ALTER TABLE IF EXISTS tenancy_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tenancy_organization ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tenancy_location ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS membership_isolation ON tenancy_membership;
CREATE POLICY membership_isolation ON tenancy_membership
  USING (user_id = current_setting('app.user_id', true));

DROP POLICY IF EXISTS organization_isolation ON tenancy_organization;
CREATE POLICY organization_isolation ON tenancy_organization
  USING (
    id = current_setting('app.organization_id', true)
    OR id IN (
      SELECT organization_id FROM tenancy_membership
      WHERE user_id = current_setting('app.user_id', true)
        AND status = 'active'
    )
  );

DROP POLICY IF EXISTS location_isolation ON tenancy_location;
CREATE POLICY location_isolation ON tenancy_location
  USING (
    organization_id = current_setting('app.organization_id', true)
    OR organization_id IN (
      SELECT organization_id FROM tenancy_membership
      WHERE user_id = current_setting('app.user_id', true)
        AND status = 'active'
    )
  );
