create table if not EXISTS image_log (
  filename string,
  event_time timestamp
);

create table if not EXISTS image_analytics (
    filename string,
    plant_type string,
    health_status string,
    confidence float,
    severity float,
    summary string,
    possible_issues string[],
    recommendations string[],
    pixel_location integer[][],
    event_time timestamp
);