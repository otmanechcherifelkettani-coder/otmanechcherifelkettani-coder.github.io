// Multilingual concept lexicons.
//
// Used in two places:
//   1. Guardrails (always on, also in live-AI mode): danger, violence/sexual, threat and
//      prompt-injection detection. Here recall matters more than precision — a false hit
//      only sends a case to a human sooner.
//   2. The simulated (demo) classifier, which stands in for the LLM when no key is set.
//
// Coverage is strongest in the 12 most common languages of the dataset. Long-tail languages
// fall through to "no positive match", which routes the case to a human instead of
// auto-resolving it (auto-resolution is allow-listed, never the default).

const rx = (parts) => new RegExp(parts.join('|'), 'iu');

export const LEX = {
  // SP-7 — danger now: medical, unresponsive, weapon, trapped, stalking in progress, minors, police.
  danger: rx([
    'unconscious', 'unresponsive', 'not responding', "isn'?t responding", "doesn'?t (answer|react|respond)", "won'?t answer", '(looks|seems) (very |really )?(ill|sick|unwell)', 'not breathing', 'seizure', 'collapsed', 'ambulance',
    'no me responde', 'no contesta', 'muy enfermo', 'se ve grave', 'muy mal',
    'no responde', 'no reacciona', 'sin responder', 'no contesta', 'inconscient', 'ne répond', 'ne repond', 'não responde', 'deixou de responder',
    'inconsciente', 'reagiert nicht', 'bewusstlos', 'svarade inte', 'svarer ikke', 'reageert niet', 'non risponde', 'svenuto', 'ambulanz',
    'ما بيرد', 'ما بيجاوب', 'ما يرد', 'فاقد الوعي', 'إسعاف', 'बेहोश', 'बोल्दैन', 'δεν απαντά', 'αισθήσεις', 'cevap vermiyor', 'bilinçsiz', 'ambulans',
    '意識がない', '反応がない', '応答がない', '返事がない', '救急', '의식이 없', '반응이 없', '구급차', '沒有反應', '冇反應', '昏迷', '救護車',
    'nie odpowiada', 'nieprzytomn', 'не відповідає', 'непритом', 'hapumui', 'hajibu',
    '\\bgun\\b', 'pistol', 'knife', 'weapon', 'pistola', 'cuchillo', 'navaja', 'arma blanca', 'couteau', '\\barme\\b', 'faca', '\\bmesser\\b', 'waffe', 'coltello',
    'سكين', 'مسدس', 'سلاح', 'चाकू', 'बंदूक', 'bıçak', 'silah', 'ナイフ', '拳銃', '칼을', '총을', '刀',
    "won'?t let me out", 'not stopping', 'not letting me out', 'no me deja bajar', 'no para', 'quiero bajarme', 'ne s.arr[eê]te pas', 'me laisse pas', 'não pára', 'não para',
    'lässt mich nicht', 'non si ferma', 'non mi fa scendere', 'لا يوقف', 'ما بيوقف', 'रुक नहीं', 'durmuyor', '止まってくれない', '안 세워', '唔停車',
    'outside my (home|house)', 'in front of my (home|house)', 'afuera de mi casa', 'devant chez moi', 'à porta de casa', 'vor meinem haus', 'voor mijn woning', 'sotto casa',
    'evimin önünde', 'まだ家の前', '집 앞에 아직', 'pod moim dom', 'біля мого будинку',
    '\\bpolice\\b', 'policía', 'polícia', '\\bpolizei\\b', 'polizia', 'شرطة', 'पुलिस', 'polis', '警察', '경찰',
    'underage', 'minors? (in danger|alone)', 'my (son|daughter|child) (is|was)', 'menor de edad', 'mineur', 'menor de idade', 'minderjährig', 'minorenne', 'قاصر', 'नाबालिग',
  ]),

  // SP-8 — violence or sexual misconduct.
  violence: rx([
    'assault', 'attacked me', '\\bhit me', 'punched', 'slapped', 'beat me', 'grabbed (my|me|her|him)', 'touch(ed)? (my|me)', 'touched me', 'groped?', 'kissed', 'sexual', 'rape', 'hand on my',
    'me agredió', 'agredid', 'agresión', 'me golpe', 'golpeó', 'me pegó', 'me tocó', 'manoseó', 'mano en la pierna', 'contacto no deseado', 'tocó mi teléfono', 'm.a agressé', 'agression', 'm.a frapp', 'm.a touché', 'contact physique',
    'me bateu', 'bateu em mim', 'me tocou', 'mão na', 'angegriffen', 'hat mich geschlagen', 'schlug mich', 'berührung', 'berührt', 'hat mich angefasst', 'aggredit', 'mi ha attaccat', 'picchiat', 'mi ha toccat', 'mishandel', 'viel me aan', 'aangevallen',
    'aangeraakt', 'aanraking', 'm-a lovit', 'saldırdı', 'dokundu', 'vurdu', 'elini diz', 'overfall', 'shambuli', 'هاجمني', 'تهجم', 'تهجّم', 'اعتدى', 'ضربني', 'لمسني', 'لمس ركبت', 'تحرش', 'हमला', 'मुझे मारा', 'छुआ', 'छेड़',
    '暴力を受け', '殴られ', '手を出され', '触られ', '脚に触れ', '体を触', '폭행', '때렸', '만져', '만지', '접촉', '打我', '摸', '非禮', 'pobił', 'dotknął', 'вдарив', 'торкнувся', 'άγγιξε', 'kosketti',
    'kaptı', 'snatched', 'arrebató', 'took hold of my', 'estiró la mano', 'manoteó', 'grbabed', '暴力を振る', 'esticou a mão', 'हाथ बढ़ा', 'مد إيده',
  ]),

  // SP-6 — harm-oriented threat phrases (credible threat), language-specific idioms.
  threatHarm: rx([
    "find (you|me)", 'track (you|me) down', 'come after', 'teach (you|me) a lesson', "you'?ll (regret|see)", 'regret it', 'or else', 'make (me|you) pay', 'menacing', 'take care of (you|me)', 'hurt (you|me)', '(?<!tried to )kill (you|me)',
    'encontrar(me|te)?', 'vas a ver', 'arrepentir', 'me la vas a pagar', 'te voy a', 'trouver', 'tu vas voir', 'leçon', 'apprendrait à vivre', 'encontrar', 'vais ver',
    'finden', 'wirst schon sehen', 'bereuen', 'trovar', 'me la farà pagare', 'vedrai', 'pentir', 'znajd', 'pożałuj', 'zobaczysz', 'vinden', 'finne meg', 'löytää',
    'ta hand om mig', 'videla, kaj se zgodi', 'blogai baigsis', 'урок', 'пожалкуєш', 'знайде', 'bulur', 'pişman', 'anjaam bura', 'अंजाम', 'पीछे आएगा', 'ढूंढ',
    'علمك', 'علّمك', 'درس', 'بلاقيك', 'يلاقيني', 'وين أنا', 'هتندم', '探し出', '探しに行', '見つけ出', '追いかけ', '見てろ', '覚えてろ', '찾아', '두고 보', '後悔', '搵上門', '嚟搵我', '找到我', '找上門',
    'utaona', 'নেব', 'পিছু', 'খুঁজে',
  ]),

  // Generic threat words. Count as safety threats unless the context is only rating/account.
  threatWord: rx(['threat', 'amenaz', 'menace', 'ameaç', 'droh', 'minacc', 'bedroh', 'grozi', 'groził', 'grasin', 'grožnj', 'تهدد', 'هدد', 'تهديد', 'धमकी', 'tehdit', '脅', '협박', '威脅', 'загроз', 'απείλ', 'uhkai']),
  ratingContext: rx(['rating', 'review', 'stars?', 'deactivat', 'ban(ned)?', 'removed', 'kicked off', 'account', 'calificaci', 'cuenta', 'desactiv', 'echaran', 'sacaran', 'arruinar',
    'classifica', 'conta', 'desativ', 'banimento', 'compte', 'désactiv', 'bannir', 'note', 'bewertung', 'konto', 'gesperrt', 'disattiv', 'valutazion', 'account', 'puan', 'hesab',
    'avstängd', 'tili', 'arvosan', 'račun', 'účt', 'konta', 'تقييم', 'حساب', 'अकाउंट', 'रेटिंग', '評価', 'アカウント', '평점', '별점', '계정', '퇴출', '評分', '帳號', 'deactivate']),

  // SP-4 — off-app payment.
  offAppCash: rx(['cash', 'efectivo', 'dinheiro', 'en liquide', 'espèces', 'bargeld', '\\bin bar\\b', 'contanti', 'kontant', 'contant', 'gotówk', 'hotovost', 'grynų', 'готівк',
    'nakit', 'taslimu', 'μετρητά', 'كاش', 'نقد', 'नकद', 'कैश', '現金', '현금', '現金', 'készpénz', 'extra money', 'pay (him|her) directly', 'más efectivo', 'dinheiro vivo', 'mais dinheiro']),

  // SP-4 — personal contact requests (number, date, address).
  personalContact: rx(['my number', 'my phone number', 'whatsapp', 'instagram', 'go out with', 'date with', '\\bsingle\\b', 'relationship status', 'where i live', 'meet up', 'number එක',
    'mi número', 'soltera', 'dónde vivo', 'salir con', 'mon numéro', 'célibataire', 'où j.habite', 'sortir avec', 'meu número', 'solteir', 'onde morava', 'mijn nummer', 'meine nummer', 'single bin', 'wo ich wohne',
    'il mio numero', 'dove abito', 'numaram', 'nerede otur', 'رقمي', 'وين ساكن', 'मेरा नंबर', 'कहाँ रहती', '連絡先', '独身', '번호를 물', '어디 사', '住哪', '男朋友', 'egyedülálló', 'hol lakom',
    'waar ik woonde', 'gdzie mieszkam', 'mój numer', 'mitt nummer', 'nambari yangu']),

  // SP-5 — discriminatory remarks.
  discrimination: rx(['racis', 'razzis', 'rassis', 'rasis', 'rasist', 'rassit', 'slur', 'discriminat', 'discrimin', 'homophob', 'xenophob', 'عنصر', '種族', '人種', '인종', 'नस्ल', 'जातिवाद',
    'वर्गवाद', 'ırkçı', 'my accent', 'mi acento', 'mon accent', 'meu sotaque', 'meines akzents', 'mio accento', 'mu aktsen', 'mój akcent', 'لهجتي', '口音', 'aksan', 'акцент', 'उच्चारण', 'উচ্চারণ', 'skąd pochodzę']),

  // SP-1 allow-list: minor conduct, comfort, lateness, route/fare, delivery service.
  minor: rx([
    '\\bac\\b', 'air con', 'temperature', 'too (hot|warm)', 'cooler air', 'music', 'radio', 'volume', 'loud', 'luggage', 'suitcase', 'trunk', 'bags', 'late', 'waited', 'route', 'detour', 'fare', 'price',
    'aire', 'calor', 'temperatura', 'música', 'musica', 'radio', 'volumen', 'maleta', 'equipaje', 'maletero', 'tarde', 'esper', 'ruta', 'precio', 'tarifa',
    'clim', 'chaud', 'musique', 'valise', 'coffre', 'retard', 'trajet', 'prix', 'ar-condicionado', 'quente', 'som', 'mala', 'porta-malas', 'atras', 'preço', 'rota',
    'klima', 'heiß', 'warm', 'musik', 'laut', 'koffer', 'kofferraum', 'verspät', 'umweg', 'preis', 'aria condizionata', 'caldo', 'bagagli', 'ritardo', 'prezzo', 'percorso',
    'klima', 'sıcak', 'müzik', 'bavul', 'bagaj', 'geç', 'fiyat', 'التكييف', 'حر', 'موسيقى', 'الشنط', 'تأخر', 'السعر', 'एसी', 'गर्मी', 'संगीत', 'गाना', 'सामान', 'देर', 'किराया',
    'エアコン', '暑', '音楽', '音量', '荷物', 'トランク', '遅', '料金', '에어컨', '더워', '음악', '짐', '트렁크', '늦', '요금', '冷氣', '太熱', '音樂', '行李', '遲到', '車費',
    'klimatyzac', 'muzyk', 'bagaż', 'spóźni', 'airco', 'muziek', 'bagage', 'laat', 'ilmastoin', 'musiikki', 'luftkonditionering', 'musik', 'bagage', 'klimaanlæg',
    'hudb', 'музик', 'гучн', 'кондиціон', 'kühl', 'enfri', 'الصوت', 'عالي', 'المكيف', 'zene', 'μουσική', 'κλιματισ', 'ζέστη', 'temperatur', 'kuuma', 'glazb', 'hlasit', 'zenét', 'muzica', 'aerul condiționat',
    'delivery', 'courier', 'food', 'intercom', 'apartment', 'repartidor', 'comida', 'livreur', 'entregador', 'kurier', 'fattorino', 'kurye', 'المندوب', '配達', '배달',
    'door', 'crumbs', 'puerta', 'migas', 'porte', 'miettes', 'tür', 'krümel', 'porta', 'briciole', 'kapı', 'باب', 'ドア', '문을', '車門',
    'phone while', 'on his phone', 'al teléfono', 'celular', 'téléphone', 'handy', 'telefono', 'telefon', 'الجوال', 'फ़ोन', '携帯', '휴대폰', '手機',
  ]),
};

// Prompt-injection patterns (text from the public is data, never instructions).
export const INJECTION = rx([
  'ignore (all )?(the )?previous instructions', 'ignore (all )?prior', 'disregard (your|all|prior|previous)', 'system override', 'admin override', '<<\\s*system', '<admin>',
  'system:', 'note to (automated|ai|bot)', 'to the automated', 'automated (reviewer|triage)', 'triage (system|bot|ai)', 'dear triage bot', 'instruction for ai', 'ai assistant:',
  'assistant, ', 'classify (this|as)', 'mark (this|as) (case )?resolved', 'do not escalate', 'do not forward to a human', 'close (it|ticket) without', 'without human review',
  'set priority to low', 'label this as no risk',
  'olvida tus instrucciones', 'para la ia', 'instrução ao sistema', 'nota para a ia', 'ignora as regras', 'note de l.utilisateur', 'classe ça', 'ne pas transmettre à un humain',
  'negeer alle eerdere', 'geautomatiseerde triage', 'nota per', 'ohita nämä', 'järjestelmä:', 'systemmelding', 'asystencie', 'nie przekazuj do człowieka',
  'للنظام الآلي', 'للذكاء الاصطناعي', 'لا تصعّد', 'नोट टू बॉट', 'असिस्टेंट', 'ट्राइएज ai', 'अ्यासिस्ट्यान्ट', 'অ্যাসিস্ট্যান্ট', 'ক্লাসিফাই',
  '自動トリアージ', '以前の指示', 'aiさんへ', '自動審核系統', '忽略先前', '唔好通知任何人', 'triage bot',
]);
