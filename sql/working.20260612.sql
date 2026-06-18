create view usatf.v_team_event_division_totals as
SELECT
    event_id,
    division,
    team,
    SUM(team_points) AS total_points,
    RANK() OVER (PARTITION BY event_id, division ORDER BY SUM(team_points) DESC) AS team_rank
FROM usatf.team_points
GROUP BY event_id, division, team
ORDER BY event_id, division, team_rank;

create view usatf.v_team_division_gender_totals as
SELECT
    division,
    gender,
    team,
    SUM(team_points) AS total_points,
    RANK() OVER (PARTITION BY division, gender ORDER BY SUM(team_points) DESC) AS team_rank
FROM usatf.team_points
GROUP BY division, gender, team
ORDER BY division, gender, team_rank;

create view usatf.v_team_division_totals as
SELECT
    division,
    team,
    SUM(team_points) AS total_points,
    RANK() OVER (PARTITION BY division ORDER BY SUM(team_points) DESC) AS team_rank
FROM usatf.team_points
GROUP BY division, team
ORDER BY division, team_rank;

create view usatf.v_team_totals as
SELECT
    team,
    SUM(team_points) AS total_points,
    RANK() OVER (ORDER BY SUM(team_points) DESC) AS team_rank
FROM usatf.team_points
GROUP BY team
ORDER BY team_rank;

alter table usatf.events 
add column col_name varchar;


alter table usatf.team_points
add CONSTRAINT team_points_event_id_fkey FOREIGN KEY (event_id) REFERENCES usatf.events(id);


--v_team_event_division_totals

CREATE OR REPLACE VIEW usatf.v_team_event_division_gender_totals
AS 
SELECT 
	event_id,
    division,
    gender,
    team,
    sum(team_points) AS total_points,
    rank() OVER (PARTITION BY event_id, division, gender ORDER BY (sum(team_points)) DESC) AS team_rank
   FROM usatf.team_points
  GROUP BY event_id, division, gender, team
  ORDER BY event_id, division, gender, (rank() OVER (PARTITION BY event_id, division ORDER BY (sum(team_points)) DESC));

alter table usatf.results 
add column comments varchar;


select 
place,
bib,
first_name,
last_name,
gender,
city,
state,
country_code,
clock_time,
chip_time,
pace,
age,
age_percentage
from htc.rsu_results
where race_id = 177384
and event_id = 1083218;

select 
seniors_m_rank,
runner,
time,
team
from usatf.individual 
where event_id = 2
and gender = 'M'
order by 1;

select 
runner,
sum(points) points
from usatf.individual_points
where gender = 'F'
group by 1
order by sum(points) desc;

alter table usatf.events 
add column url varchar;