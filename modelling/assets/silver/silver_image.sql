/* @bruin

name: silver_duck.image
type: duckdb.sql
connection: duckdb-image
materialization:
  type: table

depends:
  - raw.image_analytics
  - raw.image_log

columns:
  - name: filename
    type: string
    description: image filename (primary key)
    checks:
      - name: not_null
      - name: unique
  - name: event_time
    type: timestamp
    description: timestamp when the image was captured
    checks:
      - name: not_null
  - name: plant_type
    type: string
    description: detected plant species
  - name: health_status
    type: string
    description: health classification (healthy, diseased, unknown)
  - name: confidence
    type: float
    description: model confidence score (0.0 to 1.0)
  - name: severity
    type: float
    description: disease severity percentage
  - name: summary
    type: string
    description: AI-generated summary of plant condition
  - name: possible_issues
    type: string
    description: JSON array of possible issues
  - name: recommendations
    type: string
    description: JSON array of recommendations
  - name: heatmap
    type: string
    description: JSON array of [x, y] pixel coordinates marking points of interest

@bruin */


SELECT
    a.filename,
    l.event_time,
    a.plant_type,
    a.health_status,
    a.confidence,
    a.severity,
    a.summary,
    CAST(a.possible_issues AS VARCHAR)   AS possible_issues,
    CAST(a.recommendations AS VARCHAR)   AS recommendations,
    CAST(a.heatmap AS VARCHAR)           AS heatmap
FROM raw.image_analytics a
INNER JOIN raw.image_log l
    ON a.filename = l.filename
WHERE l.event_time IS NOT NULL
