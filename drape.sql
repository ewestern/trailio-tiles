 WITH line AS
    -- From an arbitrary line
    (SELECT way from  AS geom),
    -- (SELECT 'SRID=32632;LINESTRING (348595 4889225,352577 4887465,354784 4883841)'::geometry AS geom),
  points2d AS
    -- Extract its points
    (SELECT (ST_DumpPoints(geom)).geom AS geom FROM line),
  cells AS
    -- Get DEM elevation for each
    (SELECT p.geom AS geom, ST_Value(mnt.rast, 1, p.geom) AS val
     FROM mnt, points2d p
     WHERE ST_Intersects(mnt.rast, p.geom)),
    -- Instantiate 3D points
  points3d AS
    (SELECT ST_SetSRID(ST_MakePoint(ST_X(geom), ST_Y(geom), val), 32632) AS geom FROM cells)
-- Build 3D line from 3D points
SELECT ST_MakeLine(geom) FROM points3d;