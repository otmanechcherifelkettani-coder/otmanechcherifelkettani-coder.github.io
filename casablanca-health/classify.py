"""One classification for every source (Overture, OpenStreetMap, Google Places).

classify(name, cats) -> (main, sub) or None
  name : place name (any language)
  cats : set of lowercase category strings from the source (Overture primary/alternate categories, OSM
         amenity/healthcare/speciality values, Google primary type and types)

main classes (map layers):  L lab · H hospital/clinic/centre · D doctor · T dentist
sub classes (used by the scoring, each with its own weight):
  L   medical analysis lab (biologie médicale)            -> competitor
  LP  pathology lab (anatomie pathologique, cytology)      -> different business, not counted as competitor by default
  HP  private clinic / polyclinic / private hospital
  HL  single-specialty clinic with low lab use (eye, skin, ENT, aesthetic surgery)
  HU  public hospital, CHU, regional/provincial hospital
  CS  public primary health centre (centre de santé, CSU, dispensaire)
  MC  medical centre / group practice / SOS médecins
  HD  dialysis centre
  IM  imaging / radiology centre (orders few lab tests)
  DG  general practitioner
  DS  specialist who orders many tests (endocrino, gynéco, cardio, interne, néphro, gastro, pédiatre ...)
  DL  specialist who orders few tests (ophtalmo, dermato, ORL, psychiatre, trauma, chirurgien ...)
  DU  doctor, specialty not stated
  T   dentist
"""
import re

I = re.I
VET = re.compile(r"v[ée]t[ée]rin|\bvet\b|veterinary|بيطري", I)
PHARMA = re.compile(r"pharmac(ie|y)|parapharm|\bpara\b|صيدلية|drugstore", I)
NOT_HEALTHCARE = re.compile(
    r"optique|opticien|lunett|bijou|phone|stone|beaut|spa\b|hammam|massage|amincis|minceur|epilation|[ée]pilation|"
    r"coiff|nail|ongle|cosm[ée]ti|parfum|\bkin[ée]|r[ée][ée]ducation|physio|orthophon|psychomot|psycholog|psychoth|"
    r"psychanaly|hypno|sophrolog|coach|counsel|nutrition(?!ni)|di[ée]t[ée]ti|ost[ée]opath|podolog|chiropr|acupunct|"
    r"naturopath|hijama|حجامة|رقية|ruqya|compl[ée]mentaire|alternati|التكميلي|البديل|herb|aromath|reflexo|"
    r"d[ée]l[ée]gation|\bdirr?ection\b|minist|anapec|mutuelle|assurance|cnops\s+agence|en construction|"
    r"supplies|fournitures|mat[ée]riel m[ée]dical|[ée]quipement|equipment|jardin d.enfants|cr[èe]che|روض|preschool|"
    r"quartier|r[ée]sidence|skin clinic|body ?solution|bodysolution|biomedical alliance|pharmaceut|laboratoires? pharm|"
    r"[ée]cole|institut (sup|priv|sp[ée]cialis)|facult[ée] de|formation|universit[ée] (?!.*hospital)|lyc[ée]e|"
    r"ambulance|transport sanitaire|simulation|orthoptie|audioproth|proth[eè]se auditive|tabib\.ma|doclive|"
    r"magazine|consult(ing|ant)|recrutement|association|fondation(?! .*h[oô]pital)", I)
AESTHETIC = re.compile(r"esth[ée]ti|aesthetic|botox|filler|laser|anti[- ]?[âa]ge|greffe capillaire|medspa|beauty", I)

LAB_NAME = re.compile(
    r"\blaboratoire\b|\blaboratory\b|\blabo\b|analyses?\s+(m[ée]dical|biolog)|biologie\s+m[ée]dical|centre\s+(de\s+)?biologie|"
    r"\bbiolog|clinical lab|medical (lab|analysis)|\w{3,}lab\b|\blab\b|مختبر|تحاليل|institut pasteur|معهد باستور", I)
LAB_EXCL = re.compile(
    r"dentaire|dental|proth[eè]s|photo|تصوير|zoopole|novovet|v[ée]t[ée]rin|sanofi|sterifil|fillmed|coudon|"
    r"\bhse\b|methc|complexe sportif|lpee|essais|structures|sols|roches|التجارب|filorga|chlorophylle|lamapro|"
    r"oculaire|cosm|pharmaceut|\bliman\b|langue|language|informatique|fab ?lab|\blab(o)? (photo|num)|"
    r"sport|food|agro|alimentaire|\beaux?\b|water|environnement|chimi|multi laboratoire|lc2a|loarc|\bnational|g[ée]otech|b[ée]ton|m[ée]trolog|textile|cuir|"
    r"psycho|hypno|supplies|radio(?!.*immuno)|imagerie|scanner|\birm\b|agricultur|\bferme\b|esth[ée]ti|"
    r"municipal|hygi[èe]ne", I)
ORGANIC = re.compile(r"biologique", I)   # "agriculture biologique" unless the name also says analyses/médical
STRONG_LAB = re.compile(r"analyses?\s+(m[ée]dical|biolog)|biologie\s+m[ée]dical|centre\s+(de\s+)?biologie|"
                        r"laboratoire\s+d.analyse|مختبر\s+التح|تحاليل\s+طبية|medical\s+(lab|analysis)", I)
PATHO = re.compile(r"anatomie\s*(et\s*cytologie\s*)?patholog|anapath|\bpatholog|cytolog|histolog|التشريح|"
                   r"anatomo|path-?lab|pathology", I)

DENT = re.compile(r"dentaire|dentiste|dental|dentist|orthodont|implant|stomatolog|chirurgien[- ]dentiste|"
                  r"أسنان|الأسنان", I)
IMAGING = re.compile(r"radiolog|imagerie|\bscanner\b|\birm\b|\bmri\b|petscan|pet scan|mammograph|[ée]chograph|"
                     r"الأشعة|بالأشعة|radio\b|\bradio ", I)
DIALYSIS = re.compile(r"dialys|h[ée]modialys|rein\b|n[ée]phro.*centre|الدياليز|تصفية الدم|الكلي", I)
PUBLIC_HOSP = re.compile(r"\bh[oô]pital\b|\bhospital\b|\bchu\b|centre hospitalier|مستشفى|المستشفى", I)
PRIVATE_HOSP_HINT = re.compile(r"priv[ée]|akdital|international|clinique|clinic|hpic|cheikh khalifa|"
                               r"universit\w* international", I)
CLINIC = re.compile(r"\bclinique\b|polyclinique|\bclinic\b|\bclinical\b|\bclinica\b|مصحة|المصحة", I)
HEALTH_CENTRE = re.compile(r"centre de sant[ée]|\bcsu\b|centre sant[ée]|dispensa(ire|ry)|health cent(er|re)|"
                           r"المركز الطبي الحضري|centre de diagnostic|centre de consultation sp[ée]cialis|"
                           r"المركز الصحي|مركز صحي|centre m[ée]dico[- ]social|maison d'accouchement|dar al oumouma", I)
MED_CENTRE = re.compile(r"centre m[ée]dical|medical cent(er|re)|cabinet (de groupe|pluridisciplinaire)|"
                        r"groupe m[ée]dical|sos m[ée]dec|m[ée]decins? de garde|urgences?\b|المركز الطبي|مركز طبي", I)

GP = re.compile(r"g[ée]n[ée]raliste|m[ée]decine g[ée]n[ée]rale|m[ée]decin de famille|family (doctor|medicine|practice)|"
                r"general practi|طبيب عام|الطب العام|médecine du travail", I)
SPEC_HIGH = re.compile(
    r"endocrin|diab[ée]to|gyn[ée]co|obst[ée]tri|accouchement|fertilit|procr[ée]ation|interniste|m[ée]decine interne|"
    r"internal medicine|n[ée]phrolog|cardiolog|cardiologue|\bcardio\b|gastro|h[ée]pato|h[ée]matolog|rhumatolog|"
    r"p[ée]diatr|n[ée]onat|urolog|oncolog|canc[ée]rolog|infectiolog|pneumolog|pneumo-|allergolog|g[ée]riatr|"
    r"neurolog|maladies du sommeil|nutritionniste m[ée]decin|الغدد|السكري|أمراض النساء|التوليد|القلب|الأطفال|"
    r"الكلي|الجهاز الهضمي|الرئة|المسالك", I)
SPEC_LOW = re.compile(
    r"ophtalm|ophthalm|\boeil\b|\byeux\b|dermato|\borl\b|oto-rhino|psychiatr|addictolog|traumato|orthop[ée]d|"
    r"chirurg|anesth|m[ée]decine (du sport|physique)|sexolog|phl[ée]bolog|angiolog|stomatolog|"
    r"العيون|الجلد|الأنف|النفسي|العظام|الجراحة", I)
LOW_STRONG = re.compile(r"ophtalm|ophthalm|\boeil\b|\byeux\b|العيون|dermato|\borl\b|oto-rhino|psychiatr|"
                        r"orthop[ée]d|traumato|chirurgien (plasticien|esth)|neurochirurg", I)
LOW_CLINIC = re.compile(r"ophtalm|ophthalm|\boeil\b|\byeux\b|vision|العيون|dermato|esth[ée]ti|aesthetic|skin|"
                        r"\borl\b|psychiatr|psychiatric|addiction|plasti", I)
DOCTOR_NAME = re.compile(
    r"^\s*(dr\.?|docteur|doctor|pr\.?|professeur)\b|\bdr\.?\s|\bdocteur\b|\bpr\.\s|cabinet\b|m[ée]decin\b|"
    r"الدكتور|الطبيب|طبيب|د\.", I)

SPEC_LOW_REAL = re.compile(r"ophtalm|dermato|\borl\b|chirurg|plasticien|traumato|orthop", I)

# source categories
CAT_LAB = {"medical_lab", "laboratory_testing", "b2b_clinical_lab", "medical_laboratory", "laboratory",
           "pathology_lab", "diagnostic_services"}
CAT_DENT = {"dentist", "dental_clinic", "cosmetic_dentistry", "general_dentistry", "orthodontics",
            "pediatric_dentistry", "prosthodontics", "periodontics", "endodontics", "oral_and_maxillofacial_surgery"}
CAT_HOSP = {"hospital", "general_hospital", "emergency_department", "surgery_center", "maternity_center",
            "fertility_clinic", "clinic", "medical_clinic", "outpatient_care_facility", "medical_center",
            "dialysis_clinic", "blood_and_plasma_donation_center", "health", "health_care", "centre", "yes"}
CAT_DOCTOR = {"doctor", "doctors", "doctors_office", "family_practice", "general_practice", "internal_medicine",
              "cardiology", "dermatology", "obstetrics_and_gynecology", "pediatric_clinic", "pediatrics",
              "gastroenterology", "rheumatology", "ear_nose_and_throat", "pulmonology", "endocrinology", "oncology",
              "neurology", "urology", "nephrology", "psychiatry", "allergy_and_immunology", "orthopedics", "gerontology",
              "surgery", "plastic_and_reconstructive_surgery", "vision_or_eye_care_clinic", "ophthalmology",
              "reproductive_perinatal_and_womens_care", "prenatal_and_perinatal_care", "neuropathology",
              "infectious_disease", "hematology", "anesthesiology", "sports_medicine", "radiology",
              "behavioral_or_mental_health_clinic"}
CAT_SPEC_HIGH = {"internal_medicine", "cardiology", "obstetrics_and_gynecology", "pediatric_clinic", "pediatrics",
                 "gastroenterology", "rheumatology", "pulmonology", "endocrinology", "oncology", "neurology", "urology",
                 "nephrology", "allergy_and_immunology", "gerontology", "reproductive_perinatal_and_womens_care",
                 "prenatal_and_perinatal_care", "infectious_disease", "hematology", "gynaecology", "paediatrics",
                 "fertility_clinic"}
CAT_SPEC_LOW = {"dermatology", "ear_nose_and_throat", "psychiatry", "orthopedics", "surgery", "anesthesiology",
                "plastic_and_reconstructive_surgery", "vision_or_eye_care_clinic", "ophthalmology", "sports_medicine",
                "neuropathology", "behavioral_or_mental_health_clinic", "otolaryngology", "orthopaedics"}
CAT_EXCLUDE = {"veterinarian", "veterinary_care", "veterinary", "pharmacy", "drugstore", "beauty_salon", "spa",
               "physiotherapist", "physical_therapy", "massage_therapy", "eyewear_store", "optometry", "optician",
               "hair_salon", "nail_salon", "skin_care_clinic", "wellness_center", "chiropractic", "acupuncture",
               "speech_therapy", "psychology", "psychotherapy", "counseling", "naturopathic_medicine", "aromatherapy",
               "reflexology", "ambulance_or_ems_service", "medical_supply_store", "school", "college_university",
               "car_repair", "electronics_store", "government_office", "laser_hair_removal", "hair_replacement",
               "psychotherapist", "physiotherapist", "alternative", "podiatry", "audiology", "prosthetics", "nursing",
               "home_health_care", "medical_service_organization", "preschool", "kindergarten", "nutrition_service",
               "b2b_surgical_appliances_and_supplies", "bank_or_credit_union"}

MAIN = {"L": "L", "LP": "L", "HP": "H", "HL": "H", "HU": "H", "CS": "H", "MC": "H", "HD": "H", "IM": "H",
        "DG": "D", "DS": "D", "DL": "D", "DU": "D", "T": "T"}


def classify(name, cats):
    name = (name or "").strip()
    cats = {c.lower() for c in cats if c}
    has_spec = bool(SPEC_HIGH.search(name) or SPEC_LOW.search(name) or GP.search(name))

    if VET.search(name) or cats & {"veterinarian", "veterinary_care", "veterinary"}:
        return None
    if PHARMA.search(name) and not LAB_NAME.search(name):
        return None

    # labs: by name first (sources often file labs as "service" or "clinic"), then by category
    if re.search(r"(centre|laboratoire|cabinet)\s+(de\s+|d.)?(anatomie\s+)?patholog", name, I):
        return ("L", "LP")
    weak_lab = re.search(r"\w{3,}lab\b|\blab\b", name, I) and not re.search(
        r"\blaboratoire\b|\blabo\b|analyse|biolog|مختبر|تحاليل|pasteur", name, I)
    plural_company = re.search(r"\blaboratoires\b", name, I) and not re.search(r"analyse|biolog|m[ée]dical", name, I)
    explicit = STRONG_LAB.search(name)
    # "lab_search": returned by a keyword search for "laboratoire d'analyses médicales" (fetch_google_text.py)
    named_lab = re.search(r"\blaboratoire\b|\blabo\b|\blaboratory\b|مختبر", name, I)
    health_cat = not cats or bool(cats & (CAT_LAB | CAT_HOSP | CAT_DOCTOR)) or ("lab_search" in cats and named_lab)
    if ORGANIC.search(name) and not re.search(r"analyse|m[ée]dical", name, I):
        return None
    if LAB_NAME.search(name) and not LAB_EXCL.search(name) and not DENT.search(name) and not plural_company \
            and (explicit or health_cat) and not (weak_lab and not health_cat) \
            and not NOT_HEALTHCARE.search(name):
        return ("L", "LP") if PATHO.search(name) else ("L", "L")
    other_facility = MED_CENTRE.search(name) or CLINIC.search(name) or PUBLIC_HOSP.search(name) or \
        HEALTH_CENTRE.search(name) or DOCTOR_NAME.search(name)
    if cats & CAT_LAB and not LAB_EXCL.search(name) and not DENT.search(name) and not IMAGING.search(name) \
            and not plural_company and not other_facility:
        if NOT_HEALTHCARE.search(name):
            return None
        return ("L", "LP") if PATHO.search(name) else ("L", "L")

    if DENT.search(name) or (cats & CAT_DENT and not (has_spec and not DENT.search(name))):
        return ("T", "T")

    # non-prescribers and non-medical businesses (a named medical specialty overrides, e.g. "dermatologue ... laser")
    doctorish = bool(DOCTOR_NAME.search(name))
    if (cats & CAT_EXCLUDE or NOT_HEALTHCARE.search(name)) and not (doctorish and has_spec):
        return None
    if AESTHETIC.search(name) and not (SPEC_HIGH.search(name) or GP.search(name) or SPEC_LOW_REAL.search(name)):
        return None

    medical = bool(cats & (CAT_HOSP | CAT_DOCTOR)) or not cats  # unknown category: rely on the name
    if not medical and not (doctorish or CLINIC.search(name) or PUBLIC_HOSP.search(name)
                            or HEALTH_CENTRE.search(name)):
        return None

    if IMAGING.search(name) and not (DOCTOR_NAME.search(name) and has_spec and not re.search("radiolog", name, I)):
        return ("H", "IM")
    if DIALYSIS.search(name) or "dialysis_clinic" in cats:
        return ("H", "HD")
    if HEALTH_CENTRE.search(name):
        return ("H", "CS")
    if CLINIC.search(name) and not DOCTOR_NAME.search(name.split(" - ")[0][:4]):
        return ("H", "HL") if LOW_CLINIC.search(name) and not SPEC_HIGH.search(name) else ("H", "HP")
    if PUBLIC_HOSP.search(name):
        return ("H", "HP") if PRIVATE_HOSP_HINT.search(name) else ("H", "HU")
    if MED_CENTRE.search(name):
        return ("H", "MC")

    # doctors
    if GP.search(name):
        return ("D", "DG")
    if LOW_STRONG.search(name):
        return ("D", "DL")
    if SPEC_HIGH.search(name) or (cats & CAT_SPEC_HIGH and not SPEC_LOW.search(name)):
        return ("D", "DS")
    if SPEC_LOW.search(name) or cats & CAT_SPEC_LOW:
        return ("D", "DL")
    if cats & {"family_practice", "general_practice"}:
        return ("D", "DG")
    if DOCTOR_NAME.search(name) or cats & CAT_DOCTOR:
        return ("D", "DU")
    if cats & {"hospital", "general_hospital"} and (PUBLIC_HOSP.search(name) or CLINIC.search(name)):
        return ("H", "HU")
    if cats & {"medical_clinic", "clinic", "outpatient_care_facility", "medical_center", "surgery_center",
               "maternity_center", "fertility_clinic"}:
        # in Morocco most "medical clinic" listings without a clinic name are single practices
        return ("D", "DU")
    return None
