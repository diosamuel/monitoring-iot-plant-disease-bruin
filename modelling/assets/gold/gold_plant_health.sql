/* @bruin

name: gold_edw.plant_health
type: bq.sql
materialization:
  type: table

depends:
  - silver.image
  - silver.sensor

columns:
  - name: filename
    type: STRING
    description: image filename (primary key)
    checks:
      - name: not_null
      - name: unique
  - name: event_time
    type: TIMESTAMP
    description: timestamp of the capture
    checks:
      - name: not_null
  - name: plant_type
    type: STRING
    description: detected plant species
  - name: health_status
    type: STRING
    description: health classification
  - name: confidence
    type: FLOAT64
    description: model confidence score
  - name: severity
    type: FLOAT64
    description: disease severity percentage
  - name: summary
    type: STRING
    description: AI-generated condition summary
  - name: possible_issues
    type: STRING
    description: JSON array of possible issues
  - name: recommendations
    type: STRING
    description: JSON array of recommendations
  - name: temperature
    type: FLOAT64
    description: temperature at capture time
  - name: humidity
    type: FLOAT64
    description: humidity at capture time
  - name: soil_moisture
    type: FLOAT64
    description: soil moisture at capture time
  - name: ingested_at
    type: TIMESTAMP
    description: pipeline run timestamp
@bruin */

-- Gold layer: join image predictions with sensor readings for a complete plant health view
SELECT
    i.filename,
    i.event_time,
    i.plant_type,
    i.health_status,
    i.confidence,
    i.severity,
    i.summary,
    i.possible_issues,
    i.recommendations,
    s.temperature,
    s.humidity,
    s.soil_moisture,
    CURRENT_TIMESTAMP AS ingested_at
FROM silver.image i
LEFT JOIN silver.sensor s
    ON i.filename = s.filename
