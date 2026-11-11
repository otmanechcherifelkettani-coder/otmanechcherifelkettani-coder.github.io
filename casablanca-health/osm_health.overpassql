[out:json][timeout:180];
(
  nwr["amenity"~"^(doctors|clinic|hospital|laboratory|dentist)$"](33.45,-7.75,33.66,-7.40);
  nwr["healthcare"](33.45,-7.75,33.66,-7.40);
  nwr["name"~"laboratoire|analyses|biolog|clinique|polyclinique|h[oô]pital|cabinet|docteur|^dr[ .]|مختبر|مصحة|مستشفى|عيادة|الدكتور",i](33.45,-7.75,33.66,-7.40);
);
out center tags;
