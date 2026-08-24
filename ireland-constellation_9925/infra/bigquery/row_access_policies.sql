-- Row-level security via BigQuery Row Access Policies.
-- The policy checks whether SESSION_USER() (or a group they belong to) has a
-- row in user_access_map granting them the row's region, or an 'ALL' grant.
--
-- Note: group-based checks typically go through a Google Group used as the
-- principal in IAM; SESSION_USER() returns the calling user's email, so for
-- group-level grants you'd resolve group membership upstream (e.g. keep
-- user_access_map populated by syncing Google Group membership) rather than
-- expecting BigQuery to expand group membership at query time.

CREATE OR REPLACE ROW ACCESS POLICY region_access_policy
ON `your_project.ireland_constellation.regional_metrics`
GRANT TO ("allAuthenticatedUsers")  -- policy applies broadly; filtering happens in the WHERE below
FILTER USING (
  country_region IN (
    SELECT allowed_region
    FROM `your_project.ireland_constellation.user_access_map`
    WHERE principal = SESSION_USER()
  )
  OR EXISTS (
    SELECT 1
    FROM `your_project.ireland_constellation.user_access_map`
    WHERE principal = SESSION_USER() AND allowed_region = 'ALL'
  )
);

-- Sanity check queries (run manually, not part of policy):
-- SELECT * FROM your_project.ireland_constellation.regional_metrics; -- filtered per caller
-- SELECT session_user(); -- confirm identity BigQuery sees
