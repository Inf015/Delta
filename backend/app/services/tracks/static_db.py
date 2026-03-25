"""
Base de datos estática de los ~40 circuitos reales más comunes en Assetto Corsa.
Claves: nombre base normalizado (sin prefijos/sufijos AC).
"""

from __future__ import annotations

TRACKS: dict[str, dict] = {
    # ── Japón ──────────────────────────────────────────────────────────────────
    "suzuka": {
        "display_name": "Suzuka Circuit",
        "country": "Japón",
        "type": "real",
        "length_m": 5807,
        "turns": 18,
        "characteristics": ["técnico", "alta velocidad", "bumpy", "flujo crítico"],
        "sectors": [
            "S1: Esses + Degner — Curvas rápidas encadenadas, el flujo y el ritmo entre ellas define el sector.",
            "S2: Horquilla + Spoon — Frenadas tardías, tracción de salida esencial. Spoon exige suavidad en la entrada.",
            "S3: 130R + Chicane — 130R requiere valentía total; la chicane necesita un buen frenaje en recta.",
        ],
        "key_corners": [
            {"name": "130R", "type": "alta velocidad", "tip": "Pleno gas en setup agresivo — cualquier levantada cuesta décimas"},
            {"name": "Spoon Curve", "type": "media velocidad", "tip": "Entrada suave y progresiva; la tracción de salida es lo prioritario"},
            {"name": "Degner 2", "type": "media velocidad", "tip": "Carga lateral alta; entrada tardía abre la chicane final"},
            {"name": "Esses", "type": "alta velocidad", "tip": "Flujo continuo sin correcciones — una pisada en hierba arruina el sector"},
        ],
        "lap_record": {"time": "1:30.983", "driver": "L. Hamilton", "year": 2019, "series": "F1"},
        "notes": "El flujo de los Esses define el ritmo general de la vuelta. Pista muy exigente con el setup de dirección.",
    },

    # ── Italia ─────────────────────────────────────────────────────────────────
    "monza": {
        "display_name": "Autodromo Nazionale Monza",
        "country": "Italia",
        "type": "real",
        "length_m": 5793,
        "turns": 11,
        "characteristics": ["alta velocidad", "carga aerodinámica baja", "frenadas brutales", "slipstream decisivo"],
        "sectors": [
            "S1: Variante del Rettifilo — La primera chicane requiere frenada perfecta; la Curva Grande en pleno.",
            "S2: Lesmo 1 + Lesmo 2 + Variante Ascari — Lesmos definen la velocidad de paso; Ascari exige confianza.",
            "S3: Parabolica — Curva lenta-rápida que define la velocidad punta en la recta principal.",
        ],
        "key_corners": [
            {"name": "Parabolica (Curva Alboreto)", "type": "lenta a rápida", "tip": "Salida abierta es crítica — define la velocidad punta por la recta"},
            {"name": "Curva Grande", "type": "alta velocidad", "tip": "Pleno gas con carga baja; cualquier movimiento es catastrófico"},
            {"name": "Lesmo 1", "type": "media velocidad", "tip": "Frenada tardía, entrada en ápex tarde para abrir la salida"},
            {"name": "Variante Ascari", "type": "técnico", "tip": "Chicane de alta velocidad — la segunda parte abre la penúltima recta"},
        ],
        "lap_record": {"time": "1:21.046", "driver": "R. Barrichello", "year": 2004, "series": "F1"},
        "notes": "Pista histórica donde la resistencia aerodinámica mínima lo es todo. El setup es el polo opuesto de Mónaco.",
    },

    "mugello": {
        "display_name": "Autodromo del Mugello",
        "country": "Italia",
        "type": "real",
        "length_m": 5245,
        "turns": 15,
        "characteristics": ["técnico", "ondulado", "alta velocidad", "exigente"],
        "sectors": [
            "S1: San Donato + Luco + Poggio Secco — Zona de frenadas técnicas entre curvas de mediana velocidad.",
            "S2: Materassi + Borgo San Lorenzo — Curvas de alta velocidad con cambios de dirección rápidos.",
            "S3: Casanova + Savelli + Arrabbiata + Bucine — Las curvas más rápidas; Arrabbiata exige valentía.",
        ],
        "key_corners": [
            {"name": "Arrabbiata 1", "type": "alta velocidad", "tip": "Pleno gas requiere confianza total en el setup de dirección"},
            {"name": "San Donato", "type": "frenada pesada", "tip": "Primera curva — frenada muy tardía desde la larga recta"},
            {"name": "Bucine", "type": "lenta", "tip": "Última curva lenta — la tracción de salida define la velocidad punta"},
        ],
        "lap_record": {"time": "1:46.217", "driver": "M. Schumacher", "year": 2021, "series": "MotoGP reference"},
        "notes": "Circuito técnico y ondulado. El flujo entre curvas rápidas es la clave del tiempo de vuelta.",
    },

    "vallelunga": {
        "display_name": "Autodromo Piero Taruffi — Vallelunga",
        "country": "Italia",
        "type": "real",
        "length_m": 3240,
        "turns": 14,
        "characteristics": ["técnico", "trazado estrecho", "pocas zonas de adelantamiento"],
        "sectors": [
            "S1: Semaforo + Curva Grande — Entrada técnica y la gran curva de alta velocidad.",
            "S2: Chicane + Lunga — Zona media con cambios de dirección.",
            "S3: Tornantino + Campagnano — Curvas lentas hacia la chicane final.",
        ],
        "key_corners": [
            {"name": "Curva Grande", "type": "alta velocidad", "tip": "Pleno gas con buen aerodinámico — muy sensible al movimiento"},
            {"name": "Tornantino", "type": "horquilla", "tip": "Curva más lenta — tracción de salida define el resto del sector"},
        ],
        "notes": "Circuito compacto cerca de Roma. Popular en GT y monoplazas de fórmula.",
    },

    # ── Bélgica ────────────────────────────────────────────────────────────────
    "spa": {
        "display_name": "Circuit de Spa-Francorchamps",
        "country": "Bélgica",
        "type": "real",
        "length_m": 7004,
        "turns": 19,
        "characteristics": ["alta velocidad", "cambios de elevación", "clima impredecible", "exigente físicamente"],
        "sectors": [
            "S1: La Source + Eau Rouge/Raidillon + Kemmel — Arranque con horquilla, luego el icónico complejo de alta velocidad.",
            "S2: Les Combes + Malmedy + Rivage — Zona técnica con frenadas y curvas de mediana velocidad.",
            "S3: Pouhon + Fagnes + Stavelot + Blanchimont + Bus Stop — Curvas rápidas y la última chicane antes de la recta.",
        ],
        "key_corners": [
            {"name": "Eau Rouge / Raidillon", "type": "alta velocidad", "tip": "Pleno gas en coche competitivo — el más icónico del automovilismo"},
            {"name": "Pouhon", "type": "alta velocidad larga", "tip": "Doble curva izquierda de alta velocidad — carga lateral sostenida"},
            {"name": "Bus Stop Chicane", "type": "técnico", "tip": "Última chicane — la salida define la velocidad en la recta principal"},
            {"name": "La Source", "type": "horquilla lenta", "tip": "Primera curva — frenada desde alta velocidad, cuidado con el kerb"},
        ],
        "lap_record": {"time": "1:41.252", "driver": "V. Bottas", "year": 2018, "series": "F1"},
        "notes": "Uno de los circuitos más largos y exigentes. El clima puede cambiar entre sectores.",
    },

    # ── Reino Unido ────────────────────────────────────────────────────────────
    "silverstone": {
        "display_name": "Silverstone Circuit",
        "country": "Reino Unido",
        "type": "real",
        "length_m": 5891,
        "turns": 18,
        "characteristics": ["alta velocidad", "aerodinámico", "suave", "exigente en gomas traseras"],
        "sectors": [
            "S1: Copse + Maggotts + Becketts + Chapel — El complejo más exigente: curvas de alta velocidad encadenadas.",
            "S2: Stowe + Vale + Club — Zona más lenta con curvas de media velocidad.",
            "S3: Abbey + Farm + Village + Loop + Aintree — Mezcla de curvas rápidas y lentas hacia la recta.",
        ],
        "key_corners": [
            {"name": "Copse", "type": "alta velocidad", "tip": "Pleno gas — cualquier corrección destruye el tiempo de vuelta"},
            {"name": "Maggotts-Becketts-Chapel", "type": "alta velocidad encadenado", "tip": "La secuencia más técnica — el flujo continuo lo es todo"},
            {"name": "Stowe", "type": "frenada tardía", "tip": "Gran oportunidad de adelantamiento — frenada muy tardía posible"},
        ],
        "lap_record": {"time": "1:27.097", "driver": "M. Verstappen", "year": 2020, "series": "F1"},
        "notes": "Alta carga aerodinámica necesaria. Las gomas traseras sufren mucho en Becketts.",
    },

    "brands_hatch": {
        "display_name": "Brands Hatch",
        "country": "Reino Unido",
        "type": "real",
        "length_m": 3916,
        "turns": 20,
        "characteristics": ["técnico", "ondulado", "compacto", "emocionante"],
        "sectors": [
            "S1: Paddock Hill Bend + Druids — La cuesta descendente y la horquilla son únicos.",
            "S2: Graham Hill Bend + Surtees + McLaren — Zona técnica con curvas de mediana velocidad.",
            "S3: Clark Curve + Hawthorns + Westfield — Zona rápida hacia el final.",
        ],
        "key_corners": [
            {"name": "Paddock Hill Bend", "type": "ciega descendente", "tip": "Curva ciega sobre cresta — el punto de frenado debe memorizarse"},
            {"name": "Druids", "type": "horquilla", "tip": "Horquilla lenta — tracción de salida clave para la recta"},
        ],
        "notes": "Circuito histórico inglés muy técnico. La visibilidad reducida en varias curvas exige memorización.",
    },

    # ── Alemania ───────────────────────────────────────────────────────────────
    "nurburgring": {
        "display_name": "Nürburgring Grand Prix",
        "country": "Alemania",
        "type": "real",
        "length_m": 5148,
        "turns": 15,
        "characteristics": ["técnico", "cambios de elevación", "frío habitualmente"],
        "sectors": [
            "S1: Einfahrt + Castrol S — Arranque con zona técnica de eses.",
            "S2: Bit-Kurve + Dunlop — Curvas de media velocidad bajo el puente de Dunlop.",
            "S3: Esses Mercedes + Spitzkehre + Mercedes + Goofy — Zona lenta y técnica hacia el final.",
        ],
        "key_corners": [
            {"name": "Spitzkehre", "type": "horquilla", "tip": "Horquilla muy lenta — importante para la tracción en la subida"},
            {"name": "Castrol S", "type": "técnico", "tip": "Zona de eses en el inicio — el flujo define el ritmo del S1"},
        ],
        "lap_record": {"time": "1:28.139", "driver": "M. Schumacher", "year": 2004, "series": "F1"},
        "notes": "El GP tiene mucho menos carácter que la Nordschleife. Popular para campeonatos de GT.",
    },

    "nurburgring_nordschleife": {
        "display_name": "Nürburgring Nordschleife",
        "country": "Alemania",
        "type": "real",
        "length_m": 20832,
        "turns": 73,
        "characteristics": ["muy larga", "extremadamente técnica", "cambios de elevación masivos", "histórica"],
        "sectors": [
            "S1: Hatzenbach → Flugplatz — Zona de alta velocidad con curvas ciegas.",
            "S2: Aremberg → Fuchsröhre → Adenauer Forst — Frenadas muy tardías y curvas rápidas.",
            "S3: Karussell → Breidscheid → Döttinger Höhe — Icónica banquina de hormigón y recta final.",
        ],
        "key_corners": [
            {"name": "Karussell", "type": "banquina de hormigón", "tip": "Hay que entrar al Karussell con el coche en el hormigón — es más rápido"},
            {"name": "Schwedenkreuz", "type": "alta velocidad ciega", "tip": "Curva rápida con cresta — el coche despega levemente"},
            {"name": "Fuchsröhre", "type": "alta velocidad descendente", "tip": "Zona rápida en descenso — la tracción es limitada"},
            {"name": "Brünnchen", "type": "alta velocidad saltante", "tip": "El coche salta sobre la cresta — la suspensión y el setup son clave"},
        ],
        "notes": "El 'Green Hell'. La pista más larga y exigente del mundo. Se necesitan muchas horas para memorizarla.",
    },

    # ── España ─────────────────────────────────────────────────────────────────
    "barcelona": {
        "display_name": "Circuit de Barcelona-Catalunya",
        "country": "España",
        "type": "real",
        "length_m": 4655,
        "turns": 16,
        "characteristics": ["técnico", "equilibrado", "exigente con el setup", "pocas zonas de adelantamiento"],
        "sectors": [
            "S1: Curva 1 + Elf + Repsol — Zona de frenadas y curvas lentas hacia la subida de Europa.",
            "S2: Curva de Europa + Seat + Würth — Curvas rápidas en la parte alta del circuito.",
            "S3: Chicane + New Holland + Campsa + La Caixa — Zona técnica y la última curva lenta.",
        ],
        "key_corners": [
            {"name": "Curva 3 (Repsol)", "type": "media velocidad", "tip": "Zona de adelantamiento — frenada tardía posible con buen aerodinámico"},
            {"name": "Curva de Europa", "type": "alta velocidad", "tip": "Gran curva rápida — la carga aerodinámica aquí es muy importante"},
            {"name": "La Caixa", "type": "horquilla doble", "tip": "Doble curva lenta al final — tracción de salida define la recta principal"},
        ],
        "lap_record": {"time": "1:16.330", "driver": "M. Verstappen", "year": 2023, "series": "F1"},
        "notes": "Circuito de referencia para el desarrollo de coches. Muy exigente con el equilibrio aerodinámico.",
    },

    # ── Francia ────────────────────────────────────────────────────────────────
    "paul_ricard": {
        "display_name": "Circuit Paul Ricard",
        "country": "Francia",
        "type": "real",
        "length_m": 5842,
        "turns": 15,
        "characteristics": ["alta velocidad", "plano", "múltiples variantes", "zona azul de escape"],
        "sectors": [
            "S1: Sainte Baume + Beausset — Arranque con curvas de media velocidad.",
            "S2: Le Bendor + Le Signes — Larga recta del Mistral y la curva más rápida.",
            "S3: Chicane + Virage du pont + Chicane Ruaidh — Zona técnica final.",
        ],
        "key_corners": [
            {"name": "Signes", "type": "alta velocidad", "tip": "Pleno gas para los GT de alto nivel — la zona azul penaliza mucho"},
            {"name": "Chicane du Pont", "type": "técnico", "tip": "Última sección — el flujo de las chicanes es clave"},
        ],
        "notes": "Circuito plano con amplias zonas de escape. Usado frecuentemente para test de desarrollo.",
    },

    # ── Mónaco ─────────────────────────────────────────────────────────────────
    "monaco": {
        "display_name": "Circuit de Monaco",
        "country": "Mónaco",
        "type": "real",
        "length_m": 3337,
        "turns": 19,
        "characteristics": ["muy estrecho", "lento", "urbano", "exigente mentalmente", "sin zona de escape"],
        "sectors": [
            "S1: Sainte Dévote + Casino + Mirabeau — Arranque técnico con la curva del casino.",
            "S2: Lowes (horquilla) + Portier + Túnel — La horquilla más lenta y el túnel único.",
            "S3: Chicane del Puerto + Tabac + Piscine + La Rascasse — Zona final por el puerto.",
        ],
        "key_corners": [
            {"name": "Lowes Hairpin", "type": "horquilla más lenta del calendario", "tip": "La curva más lenta del F1 — giro de volante extremo, ida y vuelta suave"},
            {"name": "Túnel", "type": "alta velocidad ciega", "tip": "El coche acelera en la oscuridad — cuidado con el deslumbramiento al salir"},
            {"name": "Sainte Dévote", "type": "frenada desde recta", "tip": "Primera curva — muy fácil tocar el muro al frenar tarde"},
        ],
        "lap_record": {"time": "1:12.909", "driver": "L. Hamilton", "year": 2021, "series": "F1"},
        "notes": "El circuito más difícil. Un toque con los muros = carrera terminada. El ritmo es continuo y mental.",
    },

    # ── Austria ────────────────────────────────────────────────────────────────
    "red_bull_ring": {
        "display_name": "Red Bull Ring",
        "country": "Austria",
        "type": "real",
        "length_m": 4318,
        "turns": 10,
        "characteristics": ["rápido", "compacto", "muchas frenadas tardías", "pocas curvas"],
        "sectors": [
            "S1: Curva 1 + Curva 2 — Dos grandes frenadas que definen el sector.",
            "S2: Rindt + Schlossgold — Zona media con curva de alta velocidad.",
            "S3: Jochen Rindt + Zeltweg — Últimas curvas antes de la recta principal.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "Frenada enorme desde la recta — zona de adelantamiento principal"},
            {"name": "Curva 2", "type": "frenada tardía", "tip": "Segunda gran frenada seguida — el equilibrio bajo frenada es clave"},
        ],
        "lap_record": {"time": "1:02.939", "driver": "C. Leclerc", "year": 2020, "series": "F1"},
        "notes": "Circuito corto y rápido. Pocas curvas pero cada una es decisiva.",
    },

    # ── Hungría ────────────────────────────────────────────────────────────────
    "hungaroring": {
        "display_name": "Hungaroring",
        "country": "Hungría",
        "type": "real",
        "length_m": 4381,
        "turns": 14,
        "characteristics": ["técnico", "mucha carga aerodinámica", "difícil adelantamiento", "sinuoso"],
        "sectors": [
            "S1: Curva 1 + Curva 2 + Curva 3 — Zona de frenadas y curvas lentas al inicio.",
            "S2: Curva 4-9 — El sinuoso sector medio, casi como Mónaco sin muros.",
            "S3: Curva 10-14 — Zona final con chicane y la última curva hacia la recta.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "La única zona clara de adelantamiento — frenada muy tardía posible"},
            {"name": "Curva 4 (entrada sector 2)", "type": "media velocidad", "tip": "El flujo del S2 comienza aquí — la entrada determina todo el sector"},
        ],
        "lap_record": {"time": "1:15.419", "driver": "L. Hamilton", "year": 2020, "series": "F1"},
        "notes": "Circuito muy sinuoso. La carga aerodinámica máxima es necesaria. Conocido como 'Mónaco sin muros'.",
    },

    # ── Países Bajos ───────────────────────────────────────────────────────────
    "zandvoort": {
        "display_name": "Circuit Zandvoort",
        "country": "Países Bajos",
        "type": "real",
        "length_m": 4259,
        "turns": 14,
        "characteristics": ["peraltes extremos", "técnico", "histórico", "pocas zonas de adelantamiento"],
        "sectors": [
            "S1: Tarzanbocht + Gerlachbocht — Horquilla y zona inicial.",
            "S2: Hugenholtz + Motorbocht — Las curvas peraltadas únicas del circuito.",
            "S3: Arie Luyendijk + Zandvoortse bocht — Zona final con la oval peraltada.",
        ],
        "key_corners": [
            {"name": "Tarzan Hairpin", "type": "horquilla", "tip": "Principal zona de adelantamiento — frenada muy tardía desde la recta"},
            {"name": "Hugenholtz (banked)", "type": "peraltado extremo", "tip": "El peralte permite más velocidad de paso — confía en el grip"},
            {"name": "Zandvoortse Oval (banked)", "type": "peraltado", "tip": "La oval peraltada final — sensación única de G lateral sostenida"},
        ],
        "lap_record": {"time": "1:11.097", "driver": "M. Verstappen", "year": 2021, "series": "F1"},
        "notes": "Peraltes extremos en varias curvas — muy diferente a cualquier otro circuito del calendario.",
    },

    # ── Portugal ───────────────────────────────────────────────────────────────
    "portimao": {
        "display_name": "Autódromo Internacional do Algarve",
        "country": "Portugal",
        "type": "real",
        "length_m": 4653,
        "turns": 15,
        "characteristics": ["muy ondulado", "técnico", "crestas ciegas", "exigente con suspensión"],
        "sectors": [
            "S1: Curva 1 (cuesta abajo) + Curva 3 — La bajada inicial es única con la cresta ciega.",
            "S2: Curva 7-10 — Las curvas más rápidas en la parte alta.",
            "S3: Curva 11-15 — Zona final con cambios de dirección y el estadio.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "ciega descendente", "tip": "El coche pasa sobre la cresta — cuidado con el peso que se va hacia delante"},
            {"name": "Curva 5", "type": "rápida ascendente", "tip": "Alta velocidad en subida — el agarrre mejora naturalmente"},
        ],
        "notes": "Circuito muy ondulado y técnico. Las crestas ciegas hacen difícil memorizar los puntos de frenada.",
    },

    # ── Emiratos Árabes Unidos ─────────────────────────────────────────────────
    "yas_marina": {
        "display_name": "Yas Marina Circuit",
        "country": "EAU",
        "type": "real",
        "length_m": 5281,
        "turns": 16,
        "characteristics": ["mixto", "plano", "nocturno", "buenas zonas de adelantamiento"],
        "sectors": [
            "S1: Curva 1-7 — Zona de chicanes y curvas lentas.",
            "S2: Curva 8-11 — Zona de alta velocidad media.",
            "S3: Curva 12-21 — El sector técnico con el hotel del pit lane y las curvas finales.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "Primera zona de adelantamiento — frenada tardía clásica"},
            {"name": "Chicane del hotel", "type": "técnico", "tip": "Las curvas bajo el hotel — ritmo lento pero crítico para la recta"},
        ],
        "lap_record": {"time": "1:26.103", "driver": "M. Verstappen", "year": 2021, "series": "F1"},
        "notes": "Circuito nocturno bajo las luces del desierto. El calor afecta al comportamiento de las gomas.",
    },

    # ── Bahrain ────────────────────────────────────────────────────────────────
    "bahrain": {
        "display_name": "Bahrain International Circuit",
        "country": "Bahrain",
        "type": "real",
        "length_m": 5412,
        "turns": 15,
        "characteristics": ["arena", "desgaste de gomas alto", "nocturno", "frenadas importantes"],
        "sectors": [
            "S1: Curva 1-4 — Entrada con la gran frenada y la chicane.",
            "S2: Curva 5-10 — Zona de alta velocidad con varias curvas de paso medio.",
            "S3: Curva 11-15 — Zona final con la famosa frenada del último sector.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "Gran frenada desde la recta principal — zona de adelantamiento clave"},
            {"name": "Curva 10", "type": "chicane rápida", "tip": "La parte técnica del sector medio — el ritmo aquí es importante"},
        ],
        "lap_record": {"time": "1:31.447", "driver": "P. De La Rosa", "year": 2005, "series": "F1"},
        "notes": "La arena que invade la pista afecta el grip en la calificación. El desgaste de las gomas es muy alto.",
    },

    # ── China ──────────────────────────────────────────────────────────────────
    "shanghai": {
        "display_name": "Shanghai International Circuit",
        "country": "China",
        "type": "real",
        "length_m": 5451,
        "turns": 16,
        "characteristics": ["técnico", "curvas largas", "gran frenada final"],
        "sectors": [
            "S1: Curva 1-2 (larga izquierda) + Hairpin — La larga curva izquierda y la horquilla son únicas.",
            "S2: Curvas 3-10 — Zona sinuosa técnica.",
            "S3: Curvas 11-16 — Recta larga y la última chicane antes de la recta.",
        ],
        "key_corners": [
            {"name": "Curva 1-2 (larga izquierda)", "type": "muy larga", "tip": "La curva más larga del calendario — G lateral sostenida durante muchos segundos"},
            {"name": "Curva 14", "type": "frenada muy tardía", "tip": "Gran oportunidad de adelantamiento — frena muy tarde desde la recta"},
        ],
        "notes": "La larga curva izquierda del sector 1 es única en el mundo. Gran exigencia para las gomas y el cuello.",
    },

    # ── Brasil ─────────────────────────────────────────────────────────────────
    "interlagos": {
        "display_name": "Autódromo José Carlos Pace — Interlagos",
        "country": "Brasil",
        "type": "real",
        "length_m": 4309,
        "turns": 15,
        "characteristics": ["antihorario", "ondulado", "histórico", "emocionante"],
        "sectors": [
            "S1: Curva 1 + Curva 2 (S do Senna) — La frenada inicial y las eses del Senna.",
            "S2: Descida do Lago + Ferradura — Descenso técnico hacia el lago.",
            "S3: Junção + Subida dos Boxes — Ascenso final hacia la recta principal.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "Primera zona de adelantamiento antihoraria — frena muy tarde"},
            {"name": "Senna S", "type": "técnico rápido", "tip": "Las eses del Senna son muy técnicas — el flujo entre ellas es crucial"},
            {"name": "Junção", "type": "curva rápida", "tip": "La curva más rápida antes del final — G lateral alta en subida"},
        ],
        "lap_record": {"time": "1:10.540", "driver": "V. Bottas", "year": 2018, "series": "F1"},
        "notes": "Sentido antihorario. Los pilotos giran principalmente hacia la izquierda. Muy exigente físicamente.",
    },

    # ── México ─────────────────────────────────────────────────────────────────
    "mexico_city": {
        "display_name": "Autódromo Hermanos Rodríguez",
        "country": "México",
        "type": "real",
        "length_m": 4304,
        "turns": 17,
        "characteristics": ["altitud alta", "poco grip aerodinámico", "estadio", "frenadas tardías"],
        "sectors": [
            "S1: Curva 1-3 + Horquilla — Zona inicial con la triple curva y la horquilla.",
            "S2: Peraltada (estadio) — La sección del estadio con el óvalo peraltado.",
            "S3: Foro Sol — Zona técnica con el bus stop y las últimas curvas.",
        ],
        "key_corners": [
            {"name": "Peraltada", "type": "óvalo peraltado", "tip": "Solo los coches más rápidos lo toman a pleno — la altitud reduce el grip"},
            {"name": "Curva 1", "type": "frenada larga", "tip": "Gran zona de adelantamiento — los frenos trabajan mucho por la altitud"},
        ],
        "notes": "2240m sobre el nivel del mar. Los motores pierden potencia y la aerodinámica tiene menos eficiencia.",
    },

    # ── EE.UU. ─────────────────────────────────────────────────────────────────
    "cota": {
        "display_name": "Circuit of the Americas",
        "country": "USA",
        "type": "real",
        "length_m": 5513,
        "turns": 20,
        "characteristics": ["técnico", "cambios de elevación", "inspirado en otras pistas", "exigente"],
        "sectors": [
            "S1: Curva 1 (cuesta arriba ciega) + Curvas 2-9 — El inicio icónico y la zona de baja velocidad.",
            "S2: Curvas 10-15 — Zona de alta velocidad inspirada en Silverstone.",
            "S3: Curvas 16-20 — Zona final con el hairpin y las curvas de vuelta al pit.",
        ],
        "key_corners": [
            {"name": "Curva 1 (subida ciega)", "type": "ciega ascendente", "tip": "Frenas antes de ver la curva — la cresta oculta el apex hasta tarde"},
            {"name": "Curvas 3-9 (tipo Maggotts)", "type": "alta velocidad encadenado", "tip": "Inspiradas en Silverstone — el flujo entre ellas define el S1"},
            {"name": "Curva 12 (tipo 130R)", "type": "alta velocidad", "tip": "La curva más rápida — pleno gas con setup agresivo"},
        ],
        "lap_record": {"time": "1:36.169", "driver": "C. Leclerc", "year": 2019, "series": "F1"},
        "notes": "Circuito diseñado en 2012 con referencias a otras pistas históricas. Muy completo y técnico.",
    },

    "laguna_seca": {
        "display_name": "WeatherTech Raceway Laguna Seca",
        "country": "USA",
        "type": "real",
        "length_m": 3602,
        "turns": 11,
        "characteristics": ["ondulado", "icónico", "el Sacacorchos", "muy técnico"],
        "sectors": [
            "S1: Curva 1-3 + Andretti Hairpin — Zona inicial con la horquilla de Andretti.",
            "S2: Rahal Straight + Corkscrew approach — Recta hacia el icónico Sacacorchos.",
            "S3: Corkscrew + Rainey Curve + Foggy — El Sacacorchos y las curvas finales.",
        ],
        "key_corners": [
            {"name": "The Corkscrew (Curvas 8-8A)", "type": "ciega descendente extrema", "tip": "Caída de 18m en apenas 100m — frena sin ver el apex, confianza pura"},
            {"name": "Andretti Hairpin", "type": "horquilla", "tip": "Principal zona de adelantamiento — frenada tardía desde la recta"},
        ],
        "notes": "El Sacacorchos es una de las curvas más famosas del mundo. La caída de elevación es extraordinaria.",
    },

    # ── Canadá ─────────────────────────────────────────────────────────────────
    "montreal": {
        "display_name": "Circuit Gilles Villeneuve",
        "country": "Canadá",
        "type": "real",
        "length_m": 4361,
        "turns": 14,
        "characteristics": ["semipermanente", "muy rápido", "muros cerca", "frenadas extremas"],
        "sectors": [
            "S1: Curva 1-4 — Zona de chicanes iniciales.",
            "S2: Casino + Island Hairpin — La zona del casino y la horquilla central.",
            "S3: Chicane finale + Épingle — Las chicanes finales y el muro de los campeones.",
        ],
        "key_corners": [
            {"name": "Muro de los Campeones", "type": "chicane final", "tip": "El error más caro del calendario — el muro recoge a los mejores"},
            {"name": "Island Hairpin", "type": "horquilla", "tip": "La mayor zona de adelantamiento — frenada muy tardía posible"},
        ],
        "lap_record": {"time": "1:13.078", "driver": "V. Bottas", "year": 2019, "series": "F1"},
        "notes": "Pista semipermanente sobre isla. Los muros están muy cerca. El muro de los campeones es famoso.",
    },

    # ── Singapur ───────────────────────────────────────────────────────────────
    "singapore": {
        "display_name": "Marina Bay Street Circuit",
        "country": "Singapur",
        "type": "real",
        "length_m": 5063,
        "turns": 19,
        "characteristics": ["urbano", "nocturno", "muy lento", "extremadamente exigente", "caluroso"],
        "sectors": [
            "S1: Turn 1-7 — Zona inicial con varias chicanes lentas.",
            "S2: Turn 8-13 — La zona del puente Anderson y el Esplanade.",
            "S3: Turn 14-19 — Zona final por las calles.",
        ],
        "key_corners": [
            {"name": "Turn 10 (bajo el puente)", "type": "chicane", "tip": "La visibilidad cambia drásticamente al entrar y salir del puente"},
            {"name": "Turn 18", "type": "última curva", "tip": "Última curva — la salida define la velocidad en la recta principal"},
        ],
        "notes": "La carrera más larga del calendario por tiempo. El calor y la humedad son extremos. Muy exigente físicamente.",
    },

    # ── Australia ──────────────────────────────────────────────────────────────
    "albert_park": {
        "display_name": "Albert Park Circuit",
        "country": "Australia",
        "type": "real",
        "length_m": 5278,
        "turns": 16,
        "characteristics": ["semipermanente", "calles lisas", "rápido", "primera carrera del año"],
        "sectors": [
            "S1: Curva 1-4 — Zona inicial con frenada y curvas de mediana velocidad.",
            "S2: Curva 5-11 — Zona de alta velocidad por el parque.",
            "S3: Curva 12-16 — Zona final con las últimas curvas antes de la recta.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "Primera curva del año — zona de adelantamiento principal"},
            {"name": "Curva 11 (Clark Chicane)", "type": "chicane rápida", "tip": "La chicane más rápida — pleno gas para los GT"},
        ],
        "notes": "Primera carrera del Mundial de F1. Las calles del parque dan un agarre particular.",
    },

    # ── Azerbaijan ─────────────────────────────────────────────────────────────
    "baku": {
        "display_name": "Baku City Circuit",
        "country": "Azerbaiyán",
        "type": "real",
        "length_m": 6003,
        "turns": 20,
        "characteristics": ["urbano", "larga recta principal", "zona técnica medieval", "muros muy cerca"],
        "sectors": [
            "S1: Curva 1-3 — Zona de frenadas y chicanes iniciales.",
            "S2: Ciudad vieja (Curva 4-15) — La zona técnica medieval con calles muy estrechas.",
            "S3: Recta del Caspio — La recta más larga del calendario hasta la última chicane.",
        ],
        "key_corners": [
            {"name": "Curva 8 (ciudad vieja)", "type": "estrecha y técnica", "tip": "La curva más estrecha del calendario — solo un coche de ancho"},
            {"name": "Curva 1 (chicane final)", "type": "técnica", "tip": "La última frenada antes de la recta — zona de adelantamiento por DRS"},
        ],
        "notes": "La recta más larga del calendario (~2km). Las velocidades punta superan los 370 km/h.",
    },

    # ── Italia (más) ───────────────────────────────────────────────────────────
    "imola": {
        "display_name": "Autodromo Enzo e Dino Ferrari — Imola",
        "country": "Italia",
        "type": "real",
        "length_m": 4909,
        "turns": 19,
        "characteristics": ["clásico", "técnico", "anticuado", "pocas zonas de adelantamiento"],
        "sectors": [
            "S1: Tamburello + Villeneuve + Tosa — El nuevo Tamburello (chicane) y la zona del museo.",
            "S2: Piratella + Acque Minerali — La parte alta y técnica del circuito.",
            "S3: Variante Alta + Rivazza — Las curvas finales antes de la recta de pits.",
        ],
        "key_corners": [
            {"name": "Tamburello (nuevo)", "type": "chicane", "tip": "En tiempos de Senna era plena — ahora chicane lenta y técnica"},
            {"name": "Rivazza", "type": "doble curva lenta", "tip": "Doble curva al final — la salida de la segunda define la recta principal"},
            {"name": "Acque Minerali", "type": "chicane alta velocidad", "tip": "Zona con bumps — la suspensión recibe mucho en este punto"},
        ],
        "notes": "Circuito histórico donde murió Ayrton Senna en 1994. Sagrado para el automovilismo italiano.",
    },

    # ── Turquía ────────────────────────────────────────────────────────────────
    "istanbul_park": {
        "display_name": "Istanbul Park",
        "country": "Turquía",
        "type": "real",
        "length_m": 5338,
        "turns": 14,
        "characteristics": ["muy técnico", "antihorario", "Curva 8 icónica", "alta velocidad"],
        "sectors": [
            "S1: Curva 1-5 — Zona inicial con frenadas y curvas de media velocidad.",
            "S2: Curva 6-9 (Turn 8) — La icónica Curva 8, larga y muy rápida.",
            "S3: Curva 10-14 — Zona final con la recta y la última chicane.",
        ],
        "key_corners": [
            {"name": "Turn 8", "type": "cuádruple izquierda alta velocidad", "tip": "La curva más exigente del mundo — G lateral sostenida durante ~15 segundos"},
        ],
        "notes": "La Curva 8 es única en el mundo — cuádruple curva izquierda a alta velocidad. Antihorario como Brasil.",
    },

    # ── Chequia ────────────────────────────────────────────────────────────────
    "brno": {
        "display_name": "Automotodrom Brno",
        "country": "Chequia",
        "type": "real",
        "length_m": 5403,
        "turns": 14,
        "characteristics": ["ondulado", "técnico", "pocas instalaciones", "popular en moto"],
        "sectors": [
            "S1: Curva 1-4 — Zona inicial con frenadas y bajada.",
            "S2: Curva 5-9 — Zona media sinuosa.",
            "S3: Curva 10-14 — Zona final ondulada.",
        ],
        "key_corners": [
            {"name": "Curva 1", "type": "frenada pesada", "tip": "Primera zona de adelantamiento — frena desde la recta de 1km"},
        ],
        "notes": "Circuito muy popular en MotoGP. Ondulado y técnico con buenos cambios de ritmo.",
    },
}

# Alias para variantes comunes de nombres
ALIASES: dict[str, str] = {
    "red_bull_ring": "red_bull_ring",
    "spielberg": "red_bull_ring",
    "a1_ring": "red_bull_ring",
    "yas_marina": "yas_marina",
    "abu_dhabi": "yas_marina",
    "albert_park": "albert_park",
    "melbourne": "albert_park",
    "hermanos_rodriguez": "mexico_city",
    "mexico": "mexico_city",
    "gilles_villeneuve": "montreal",
    "circuit_gilles_villeneuve": "montreal",
    "marina_bay": "singapore",
    "nordschleife": "nurburgring_nordschleife",
    "nords": "nurburgring_nordschleife",
    "circuit_de_catalunya": "barcelona",
    "catalunya": "barcelona",
    "spa_francorchamps": "spa",
    "francorchamps": "spa",
    "paul_ricard": "paul_ricard",
    "le_castellet": "paul_ricard",
    "istanbul": "istanbul_park",
    "laguna": "laguna_seca",
    "cota": "cota",
    "americas": "cota",
}


def lookup(track_id: str) -> dict | None:
    """
    Busca un track_id normalizado en la base de datos estática.
    Retorna el dict de info o None si no se encuentra.
    """
    if track_id in TRACKS:
        return TRACKS[track_id]
    if track_id in ALIASES:
        return TRACKS.get(ALIASES[track_id])
    return None
