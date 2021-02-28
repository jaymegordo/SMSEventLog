select * From ComponentType a
where a.EquipClass='Truck_Electric'

-- group by component
order by component

-- INSERT INTO ComponentType (Component, Modifier, Floc, EquipClass)
-- VALUES
-- ('D-Ring Bolts', NULL, 'D_RING', 'Truck_Electric'),
-- ('Heat Exchanger', NULL, 'HEAT_EXCH', 'Truck_Electric'),
-- ('Orbital Valve', NULL, 'ORBITAL_VALVE', 'Truck_Electric'),
-- ('Pre Lube Pump', NULL, 'PRELUBE_PUMP', 'Truck_Electric')