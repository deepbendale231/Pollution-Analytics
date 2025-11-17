USE air_quality_db;

SELECT * FROM air_quality LIMIT 10;

-- 🔍 SECTION 1: BASIC OVERVIEW
-- =========================================================
SELECT DISTINCT country FROM air_quality;

SELECT COUNT(DISTINCT city) AS total_cities FROM air_quality;

SELECT COUNT(DISTINCT station) AS total_stations FROM air_quality;

-- =========================================================
-- 📊 SECTION 2: CORE KPIs
-- =========================================================

-- Average pollution by city
SELECT city, ROUND(AVG(pollutant_avg),2) AS avg_pollution
FROM air_quality
GROUP BY city
ORDER BY avg_pollution DESC
LIMIT 10;

-- Most polluted station per city
SELECT city, station, MAX(pollutant_avg) AS max_pollution
FROM air_quality
GROUP BY city, station
ORDER BY max_pollution DESC
LIMIT 10;

-- Average pollution by pollutant type
SELECT pollutant_id, 
       ROUND(AVG(pollutant_min),2) AS avg_min,
       ROUND(AVG(pollutant_max),2) AS avg_max,
       ROUND(AVG(pollutant_avg),2) AS avg_pollution
FROM air_quality
GROUP BY pollutant_id;

-- Overall KPIs
SELECT 
    ROUND(AVG(pollutant_avg),2) AS overall_avg_pollution,
    MAX(pollutant_max) AS peak_pollution,
    COUNT(*) AS total_records
FROM air_quality;

-- =========================================================
-- 📅 SECTION 3: TIME-BASED ANALYSIS
-- =========================================================

-- Daily average pollution
SELECT DATE(last_update) AS date, 
       ROUND(AVG(pollutant_avg),2) AS daily_avg
FROM air_quality
GROUP BY DATE(last_update)
ORDER BY date;

-- Monthly pollution trend
SELECT DATE_FORMAT(last_update, '%Y-%m') AS month, 
       ROUND(AVG(pollutant_avg),2) AS monthly_avg
FROM air_quality
GROUP BY DATE_FORMAT(last_update, '%Y-%m')
ORDER BY month;

-- =========================================================
-- 🚨 SECTION 4: THRESHOLD & EXCEEDANCE ANALYSIS
-- =========================================================

-- Count of unsafe readings (>100)
SELECT COUNT(*) AS exceedances, 
       ROUND(COUNT(*) / (SELECT COUNT(*) FROM air_quality) * 100,2) AS percentage_exceedance
FROM air_quality
WHERE pollutant_avg > 100;

-- City-wise exceedances
SELECT city, COUNT(*) AS exceed_count
FROM air_quality
WHERE pollutant_avg > 100
GROUP BY city
ORDER BY exceed_count DESC
LIMIT 10;

-- =========================================================
-- 📍 SECTION 5: LOCATION-BASED INSIGHTS
-- =========================================================

-- Average pollution with coordinates
SELECT city, latitude, longitude, ROUND(AVG(pollutant_avg),2) AS avg_pollution
FROM air_quality
GROUP BY city, latitude, longitude;

-- Top 10 cities by pollution with coordinates
SELECT city,
       ROUND(AVG(pollutant_avg), 2) AS avg_pollution
FROM air_quality
GROUP BY city
ORDER BY avg_pollution DESC
LIMIT 10;

-- OTHER INDICATORS 

-- Pollution volatility (max-min difference)
SELECT city,
       ROUND(AVG(pollutant_max - pollutant_min),2) AS avg_volatility
FROM air_quality
GROUP BY city
ORDER BY avg_volatility DESC
LIMIT 10;

-- Correlation proxy (pollutant_max vs avg)
SELECT 
    ROUND(AVG(pollutant_max),2) AS avg_max,
    ROUND(AVG(pollutant_avg),2) AS avg_mean,
    ROUND(AVG(pollutant_max - pollutant_avg),2) AS avg_difference
FROM air_quality;