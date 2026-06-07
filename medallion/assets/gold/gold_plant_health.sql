/* @bruin

name: gold.plant_health
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
  - name: heatmap
    type: STRING
    description: JSON array of [x, y] pixel coordinates
  - name: reading_count
    type: INT64
    description: number of sensor readings for this image period
  - name: avg_temperature
    type: FLOAT64
    description: average temperature at capture period
  - name: avg_humidity
    type: FLOAT64
    description: average humidity at capture period
  - name: avg_soil_moisture
    type: FLOAT64
    description: average soil moisture at capture period
  - name: ingested_at
    type: TIMESTAMP
    description: pipeline run timestamp
@bruin */

-- Gold layer: join image predictions with aggregated sensor readings for a complete plant health view
SELECT
    i.filename,
    i.event_time,
    i.health_status,
    i.confidence,
    i.severity,
    i.summary,
    i.possible_issues,
    i.recommendations,
    i.heatmap,
    agg.reading_count,
    agg.avg_temperature,
    agg.avg_humidity,
    agg.avg_soil_moisture,
    CURRENT_TIMESTAMP() AS ingested_at
FROM silver.image i
LEFT JOIN (
    SELECT
        filename,
        COUNT(*)           AS reading_count,
        AVG(temperature)   AS avg_temperature,
        AVG(humidity)      AS avg_humidity,
        AVG(soil_moisture) AS avg_soil_moisture
    FROM silver.sensor
    GROUP BY filename
) agg
    ON i.filename = agg.filename
