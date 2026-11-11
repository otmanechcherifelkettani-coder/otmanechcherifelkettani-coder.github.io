[out:json][timeout:600];
(
  nwr["amenity"~"^(doctors|clinic|hospital|laboratory|dentist)$"](32.29,-9.07,33.84,-6.75);
  nwr["healthcare"](32.29,-9.07,33.84,-6.75);
  nwr["name"~"laboratoire|analyses|biolog|clinique|polyclinique|h[oô]pital|cabinet|docteur|^dr[ .]|مختبر|مصحة|مستشفى|عيادة|الدكتور",i](32.29,-9.07,33.84,-6.75);
);
out center tags;
