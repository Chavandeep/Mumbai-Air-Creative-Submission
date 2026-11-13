"""Recommendation content. Evidence strings are filled with numbers computed from the data at run time
(see views/recommendations.py). Ratings are ordinal editorial judgements, shown and adjustable in the app."""

# rating scale: 3 = strong / easy / low, 1 = weak / hard / high (always "3 is better")
RECS = [
    {
        "id": "road_dust", "theme": "Road infrastructure", "title": "Treat road dust as infrastructure, not housekeeping",
        "problem": "Silt on carriageways and unpaved shoulders is ground up and thrown back into the air by every passing vehicle.",
        "evidence": "The NEERI-IIT Bombay inventory attributes {road_dust_pm:.0f}% of Mumbai's total particulate load to paved and unpaved road dust. "
                    "BMC's street layer holds {road_km:,.0f} km of streets; carriageway width is recorded for only {width_known:.0f}% of that length, so the city cannot yet say where its shoulders are unpaved.",
        "intervention": "Wall-to-wall paving of shoulders on every street of 9 m or wider, mechanised sweeping and washing on a published schedule, and a 48-hour rule for reinstating utility trenches.",
        "mechanism": "Removes the silt reservoir that traffic resuspends, and seals the surfaces that keep refilling it.",
        "benefits": "Acts on the largest single source of coarse particles; benefits concentrate along the busiest corridors where people walk and wait.",
        "limits": "Mostly coarse particles (PM10): the effect on PM2.5 is smaller than the effect on PM10. Sweeping without washing can raise dust. Needs treated water and sustained contracts.",
        "data_needed": "Silt-load sampling by road class, a complete carriageway and shoulder inventory, and kerbside PM10 and PM2.5 before and after on treated and untreated streets.",
        "ratings": {"mass": 3, "feasibility": 3, "cost": 2, "complexity": 3},
    },
    {
        "id": "construction", "theme": "Construction", "title": "Make dust control a condition of every building permit",
        "problem": "Demolition, excavation, material handling and truck movements release dust at thousands of sites spread through residential streets.",
        "evidence": "BMC's property register lists {uc_buildings:,} buildings as under construction, the most in {uc_top} wards. The NEERI-IIT Bombay inventory assigns {construction_pm:.0f}% of particulate load to construction including Metro works. "
                    "The app has no measured construction-activity data: this is the largest evidence gap.",
        "intervention": "Permit-linked site barriers, continuous misting during demolition and excavation, covered stockpiles and trucks, wheel washing, and a public register of active sites with sensor readings at the boundary.",
        "mechanism": "Suppresses dust at the point of release and stops it being tracked on to roads, where it becomes road dust.",
        "benefits": "Cuts very local, very high exposures next to homes and schools; also reduces the road-dust reservoir.",
        "limits": "Enforcement capacity is the constraint, not technology. Benefits are local and hard to see at a monitor several kilometres away.",
        "data_needed": "Geocoded commencement and completion certificates, site-boundary PM sensors, and truck-trip logs.",
        "ratings": {"mass": 2, "feasibility": 3, "cost": 3, "complexity": 2},
    },
    {
        "id": "waste", "theme": "City planning", "title": "End open and landfill burning",
        "problem": "Burning refuse emits fine particles at ground level, often at night, in the neighbourhoods least able to avoid them.",
        "evidence": "Shivaji Nagar, in M / East ward where the Deonar dumping ground lies, recorded {sn_spike_hours} spike hours (at least three times its typical level and above 100 µg/m³), against {other_spike_max} at the next-highest station. "
                    "SAFAR's 2019-20 inventory puts municipal waste at {waste_pm25:.1f}% of PM2.5 emissions. The link between this station's spikes and burning is a hypothesis the timing supports, not a proven cause.",
        "intervention": "Thermal cameras and gas wells at landfills, guaranteed daily collection in the wards around them, and ward-level response teams for roadside burning.",
        "mechanism": "Removes a combustion source that emits almost entirely in the fine (PM2.5) range.",
        "benefits": "Targets PM2.5 directly and the worst short-term peaks; large equity benefit for M/East ward.",
        "limits": "Landfill fires are hard to extinguish once deep-seated. Requires waste to go somewhere else: processing capacity must come first.",
        "data_needed": "Fire logs with timestamps and locations, to test against the hourly record; chemical speciation at Shivaji Nagar during spikes.",
        "ratings": {"mass": 2, "feasibility": 2, "cost": 2, "complexity": 2},
    },
    {
        "id": "freight", "theme": "Transportation", "title": "Clean up heavy diesel first",
        "problem": "A small number of heavy diesel vehicles emit most of the transport sector's particles.",
        "evidence": "In the NEERI-IIT Bombay inventory heavy diesel vehicles account for {hddv_share:.0f}% of all vehicle-exhaust particulate, far more than cars and two-wheelers combined. "
                    "SAFAR estimates transport at {transport_pm25:.1f}% of PM2.5 emissions in 2019-20.",
        "intervention": "Low-emission freight windows on arterial roads, scrappage or retrofit of pre-BS-IV trucks and buses, and electric or CNG replacement of the oldest BEST and contract buses.",
        "mechanism": "Removes the highest-emitting engines from the busiest corridors; exhaust particles are almost all PM2.5.",
        "benefits": "High return per vehicle; also cuts NOx and noise.",
        "limits": "Freight is regional: trucks registered elsewhere need port and toll-point enforcement. Fleet turnover takes years.",
        "data_needed": "Classified traffic counts by hour on arterial roads, and remote-sensing emission tests by vehicle class.",
        "ratings": {"mass": 2, "feasibility": 2, "cost": 2, "complexity": 2},
    },
    {
        "id": "transit", "theme": "Transportation", "title": "Close the last-mile gaps to rail and bus",
        "problem": "Where the walk to a station is long, short trips shift to autos, two-wheelers and cars.",
        "evidence": "{best_city:.0f}% of residential floor area is within 400 m of a BEST stop, but only {rail_city:.0f}% is within 1 km of a suburban station - from {rail_low:.0f}% in {rail_low_ward} to {rail_high:.0f}% in {rail_high_ward}. "
                    "The stop layer carries no routes or frequencies, so this measures proximity, not service.",
        "intervention": "Frequent feeder buses and continuous footpaths within 1 km of every suburban and metro station, prioritised in the wards with the lowest rail access.",
        "mechanism": "Makes the low-emission trip the convenient one, reducing vehicle kilometres and congestion.",
        "benefits": "Compounds over time; large co-benefits for safety, access to jobs and carbon.",
        "limits": "Slow to show up in air quality. Mode shift depends on frequency and reliability, which this dataset cannot see.",
        "data_needed": "GTFS frequencies, ridership by stop, and footpath continuity surveys.",
        "ratings": {"mass": 2, "feasibility": 2, "cost": 1, "complexity": 1},
    },
    {
        "id": "fuel", "theme": "Industrial emissions", "title": "Move bakeries, eateries and crematoria off wood and coal",
        "problem": "Small commercial combustion sits inside dense neighbourhoods and vents at street level.",
        "evidence": "Bakeries alone are {bakery_pm:.1f}% of particulate load in the NEERI-IIT Bombay inventory - more than all cars, taxis and two-wheelers. The same study puts the city's remaining industry and power at {industry_pm:.1f}%, "
                    "because the main power plant's tall stacks disperse beyond the city.",
        "intervention": "Time-bound conversion to piped gas or electric ovens with a connection subsidy; electric or gas furnaces alongside traditional pyres at crematoria.",
        "mechanism": "Replaces solid-fuel combustion with fuels that emit a small fraction of the particles.",
        "benefits": "Fine-particle reductions exactly where population density is highest.",
        "limits": "Many units are small and informal; conversion needs gas network reach and working capital.",
        "data_needed": "A geocoded register of solid-fuel commercial units and their fuel use.",
        "ratings": {"mass": 1, "feasibility": 3, "cost": 3, "complexity": 2},
    },
    {
        "id": "green", "theme": "Urban greenery", "title": "Build the parks the Development Plan already reserves - worst-served wards first",
        "problem": "Park access is unequal, and vegetation is too often proposed as an air-pollution fix it cannot be.",
        "evidence": "{park_city:.0f}% of residential floor area is within 500 m of a mapped park, from {park_low:.0f}% in {park_low_ward} to {park_high:.0f}% in {park_high_ward}. "
                    "The Development Plan 2034 reserves {dp_sites:,} further open-space plots; building them all would raise access to {park_after:.0f}% (scenario result).",
        "intervention": "Acquire and open reserved open-space plots in the wards with the lowest access first, and plant dense hedges - not tall canopy - between arterial roads and footpaths, schools and clinics.",
        "mechanism": "Parks displace emitting land uses and give people clean-air space; low hedges at the kerb reduce pedestrian exposure without trapping exhaust.",
        "benefits": "Heat, flooding, health and equity gains are large and well evidenced.",
        "limits": "City-wide PM2.5 removal by vegetation is small - a few percent at most in published reviews. Reserved plots are often encumbered. Parks here are points without area, so quality is unmeasured.",
        "data_needed": "Park polygons with area and canopy cover, and the legal status of each reservation.",
        "ratings": {"mass": 1, "feasibility": 2, "cost": 1, "complexity": 1},
    },
    {
        "id": "monitor", "theme": "City planning", "title": "Measure where the questions are",
        "problem": "A few dozen PM2.5 stations cannot resolve differences between neighbourhoods, and their records include implausible readings that have to be screened out by hand.",
        "evidence": "Across {n_assoc} stations, no measure of surroundings - buildings, roads, bus stops, parks - shows a rank correlation with 2024 median PM2.5 stronger than {max_rho:.2f} at any radius. "
                    "In the four-station record {time_pct:.0f}% of hourly variation is common to all stations. {flagged} readings above 1,000 µg/m³ had to be excluded, including values near 100,000.",
        "intervention": "A dense, calibrated low-cost sensor layer at kerbsides, construction boundaries, landfill edges and schools, with automatic fault flagging and open hourly data, plus PM10 and speciation at reference stations.",
        "mechanism": "Turns planning debates into testable before-and-after comparisons.",
        "benefits": "Every other recommendation here becomes measurable.",
        "limits": "Sensors need co-location calibration in humid coastal air; data without enforcement changes nothing.",
        "data_needed": "This is the data.",
        "ratings": {"mass": 1, "feasibility": 3, "cost": 3, "complexity": 3},
    },
]

CRITERIA = {
    "mass": ("Share of emitted particles addressed", "From the two published inventories: 3 = the largest source in either inventory, 1 = small or indirect."),
    "feasibility": ("Feasibility", "3 = within BMC's existing powers and contracts, 1 = needs new institutions or regional coordination."),
    "cost": ("Cost", "3 = low public cost, 1 = major capital programme. Ordinal only - no rupee figures are claimed."),
    "complexity": ("Implementation simplicity", "3 = one agency, repeatable, 1 = many agencies, land or behaviour change."),
}
