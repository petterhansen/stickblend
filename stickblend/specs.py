"""Figuren-Steckbriefe. Eine neue Figur = ein neuer Eintrag (siehe STICKMAN-WORKFLOW.md).

Felder (alle optional ausser name/torso):
  height            Koerpergroesse in m (Standard 1.75)
  prop              Proportionen relativ zur Hoehe: head, torso, leg, arm
  shoulderW         halbe Schulterbreite (m)
  skin              Hautfarbe (Kopf, Haende)
  limbs             Farbe der Strichglieder (Standard: Tusche)
  torso             {color, width, depth, profile, details: [...]}
                    details: buttons, placket, strap, belt, collar, pockets, pouches, camera, bowtie, tie (length, blow), hood, panel, tabs
  sleeves / pants   {color, len (0..1), r}  -> Stoff ueber den Strichgliedern
  puttees, shoes    Farben
  hair              {style: short|bowl|bob|long|sides|none, color, volume}
  hat               {type: fieldcap|officer|beanie|cap|helmet|hardhat, color, frayed}
  extras            ["glasses", "headband", "backpack", "lifepack"]
  face              {stubble, age, nose, blush, eye_highlight}
"""

OLIVE, OLIVE_OLD = "8a8a4a", "7d7a48"

SPECS = {
    # ---------- Wolkenkratzer (Technikgeschosse) ----------
    "du": {
        "name": "Du (tuerkiser Hoodie)", "shoulderW": 0.16,
        "torso": {"color": "17b8b0", "details": [{"type": "hood", "color": "12a39c"}]},
        "shoes": "2a2a33", "hair": {"style": "short", "color": "3a2a20"}, "face": {"nose": True},
    },
    "inspector": {
        "name": "Bauprüfer", "shoulderW": 0.17, "height": 1.74,
        "torso": {"color": "7d828c", "details": [{"type": "panel", "color": "f2f0ea", "width": 0.3, "y0": 0.6},
                                                 {"type": "tie", "color": "d8262c", "length": 0.62},
                                                 {"type": "buttons", "color": "4a4e56", "y0": 0.14, "y1": 0.44}]},
        "shoes": "2a2420", "hat": {"type": "hardhat", "color": "f5c518"}, "face": {"nose": True, "age": 1},
    },
    # ---------- Hiroo Onoda ----------
    "onoda": {
        "name": "Leutnant Onoda (1944)", "shoulderW": 0.17,
        "torso": {"color": OLIVE, "details": [{"type": "placket"}, {"type": "buttons", "color": "c9a650"}, {"type": "collar"}, {"type": "tabs", "color": "c8352f"},
                                              {"type": "belt", "color": "6b4a2a", "buckle": "b8963a"}, {"type": "strap", "color": "6b4a2a"}, {"type": "pouches", "n": 3, "color": "7a5232"}]},
        "shoes": "3a2a1e",
        "hat": {"type": "fieldcap", "color": OLIVE}, "face": {"nose": True},
    },
    "onodaOld": {
        "name": "Onoda (1974)", "shoulderW": 0.16,
        "torso": {"color": OLIVE_OLD, "details": [{"type": "placket"}, {"type": "buttons", "color": "a89060"}, {"type": "collar"}, {"type": "tabs", "color": "a0302a"},
                                                  {"type": "belt", "color": "6b4a2a", "buckle": "8a7a3a"}, {"type": "strap", "color": "5a3a24"}, {"type": "pouches", "n": 2, "color": "7a5232"},
                                                  {"type": "patch", "color": "4f6a3a", "phi": -0.7, "y": 0.55}, {"type": "patch", "color": "7a5a3a", "phi": 0.9, "y": 0.35}]},
        "shoes": "4a3020",
        "hat": {"type": "fieldcap", "color": OLIVE_OLD, "frayed": True}, "face": {"nose": True, "stubble": True, "age": 2},
    },
    "tani": {
        "name": "Major Taniguchi (1944)", "shoulderW": 0.18,
        "torso": {"color": "7f7a46", "details": [{"type": "placket"}, {"type": "buttons", "color": "c9a650"}, {"type": "collar"}, {"type": "tabs", "color": "c8352f"},
                                                 {"type": "belt", "color": "4a3020", "buckle": "c9a650"}, {"type": "strap", "color": "4a3020"}]},
        "shoes": "2a1e16",
        "hat": {"type": "officer", "color": "7f7a46"}, "extras": ["glasses"], "face": {"nose": True},
    },
    "taniOld": {
        "name": "Taniguchi (1974, Buchhaendler)", "shoulderW": 0.165, "height": 1.7,
        "torso": {"color": "4a4540", "details": [{"type": "panel", "color": "e8e8e8", "width": 0.55, "y0": 0.45}, {"type": "buttons", "color": "2a2a2a", "y0": 0.1, "y1": 0.4}]},
        "shoes": "2a1e16",
        "hair": {"style": "sides", "color": "cfcfcf"}, "extras": ["glasses"], "face": {"nose": True, "age": 3},
    },
    "suzuki": {
        "name": "Norio Suzuki (1974)", "shoulderW": 0.16,
        "torso": {"color": "4a6a9a", "details": [{"type": "placket", "color": "2f4a70"}, {"type": "pockets", "color": "3f5f8f"}, {"type": "collar", "color": "3f5f8f"}]},
        "shoes": "6b4a2a",
        "hair": {"style": "long", "color": "1c1a20"}, "extras": ["headband", "backpack"], "face": {"nose": True},
    },
    "comrade": {
        "name": "Kamerad", "shoulderW": 0.18, "height": 1.7,
        "torso": {"color": OLIVE, "details": [{"type": "placket"}, {"type": "buttons", "color": "c9a650"}, {"type": "collar"}, {"type": "tabs", "color": "c8352f"},
                                              {"type": "belt", "color": "6b4a2a", "buckle": "b8963a"}, {"type": "pouches", "n": 3, "color": "7a5232"}]},
        "shoes": "3a2a1e",
        "hat": {"type": "fieldcap", "color": OLIVE}, "face": {"nose": True},
    },
    # ---------- Referenzstil (moderne Alltagsfiguren) ----------
    "astronaut": {
        "name": "Astronaut (1969)", "shoulderW": 0.18,
        "torso": {"color": "eceef2", "width": 1.18, "details": [{"type": "patch", "color": "8e949e", "phi": 0.0, "y": 0.62, "size": (0.13, 0.08)},
                                                               {"type": "patch", "color": "c8352f", "phi": -0.95, "y": 0.8, "size": (0.06, 0.04)},
                                                               {"type": "belt", "color": "c4c8d0", "buckle": "8a8e96"}]},
        "shoes": "d8dade", "hat": {"type": "helmet"}, "extras": ["lifepack"], "hair": {"style": "short", "color": "6a4a2a"}, "face": {"nose": False},
    },
    "tourist": {
        "name": "Tourist (Hoodie)", "shoulderW": 0.15,
        "torso": {"color": "f07a1a", "width": 1.12, "details": [{"type": "camera", "color": "2a2a2e"}]},
        "hair": {"style": "bowl", "color": "5a3a26", "volume": 1.12}, "shoes": "3a2a22", "face": {"nose": False},
    },
    "clerk": {
        "name": "Verkaeuferin (Anzug)", "shoulderW": 0.14, "height": 1.62,
        "torso": {"color": "2a2438", "pattern": "pinstripe", "pattern_color": "4a4460", "details": [{"type": "panel", "color": "f4f4f0", "width": 0.35, "y0": 0.62}, {"type": "bowtie", "color": "d4322c"}]},
        "hair": {"style": "bob", "color": "15151a"}, "shoes": "15151a", "face": {"nose": False, "eyes": "white"},
    },
    "prospector": {
        "name": "Goldsucher (Karohemd)", "shoulderW": 0.15,
        "torso": {"color": "b8452a", "pattern": "plaid", "pattern_color": "5a1a12", "details": [{"type": "placket", "color": "5a1a12"}, {"type": "buttons", "color": "e8d8b0"}]},
        "hat": {"type": "beanie", "color": "d8a838"}, "shoes": "3a2418", "face": {"nose": False, "eyes": "white"},
    },
    "kid": {
        "name": "Kind (Pullover)", "shoulderW": 0.12, "height": 1.25, "prop": {"head": 0.17},
        "torso": {"color": "7a4fd0", "details": [{"type": "collar", "color": "5a35a8"}]},
        "hair": {"style": "short", "color": "2a1c14"}, "shoes": "c23a2a", "face": {"nose": False, "blush": True},
    },
    # ---------- The Pig War (1859) ----------
    "cutlar": {
        "name": "Lyman Cutlar (Farmer)", "shoulderW": 0.16,
        "torso": {"color": "b85a32", "pattern": "plaid", "pattern_color": "5a2414",
                  "details": [{"type": "placket", "color": "5a2414"}, {"type": "buttons", "color": "e8d8b0"},
                              {"type": "belt", "color": "4a301e", "buckle": "c9a650"}]},
        "hat": {"type": "cap", "color": "7a5a38"}, "shoes": "3a2418",
        "face": {"nose": True, "stubble": True},
    },
    "griffin": {
        "name": "Charles Griffin (HBC)", "shoulderW": 0.165, "height": 1.78,
        "torso": {"color": "2b2c38", "pattern": "pinstripe", "pattern_color": "4e5068",
                  "details": [{"type": "panel", "color": "f2f0ea", "width": 0.36, "y0": 0.58},
                              {"type": "bowtie", "color": "8a2424"}, {"type": "buttons", "color": "1a1a20", "y0": 0.12, "y1": 0.45}]},
        "hair": {"style": "sides", "color": "5a4a3a"}, "extras": ["glasses"], "shoes": "1a181c",
        "face": {"nose": True, "age": 2},
    },
    "pickett": {
        "name": "Captain George Pickett (US)", "shoulderW": 0.175,
        "torso": {"color": "24365a", "details": [{"type": "placket", "color": "182540"}, {"type": "buttons", "color": "e0bc52"},
                                                 {"type": "collar", "color": "182540"}, {"type": "tabs", "color": "e0bc52"},
                                                 {"type": "belt", "color": "2a1e16", "buckle": "e0bc52"}, {"type": "strap", "color": "2a1e16"}]},
        "hat": {"type": "officer", "color": "24365a"}, "shoes": "221814",
        "face": {"nose": True},
    },
    "us_soldier": {
        "name": "US Soldier (1859)", "shoulderW": 0.165, "height": 1.72,
        "torso": {"color": "2e4674", "details": [{"type": "placket", "color": "1f3254"}, {"type": "buttons", "color": "d8b44c"},
                                                 {"type": "belt", "color": "2a1e16", "buckle": "d8b44c"}, {"type": "pouches", "n": 2, "color": "3a281c"}]},
        "hat": {"type": "fieldcap", "color": "2e4674"}, "shoes": "2a1e16",
        "face": {"nose": True},
    },
    "uk_marine": {
        "name": "British Royal Marine (1859)", "shoulderW": 0.17, "height": 1.74,
        "torso": {"color": "b82424", "details": [{"type": "placket", "color": "8a1818"}, {"type": "buttons", "color": "e8c858"},
                                                 {"type": "collar", "color": "1c2640"},
                                                 {"type": "belt", "color": "edeae0", "buckle": "e8c858"}, {"type": "strap", "color": "edeae0"}]},
        "hat": {"type": "officer", "color": "1e2028"}, "shoes": "1a181a",
        "face": {"nose": True},
    },
    "baynes": {
        "name": "Admiral Robert Baynes (RN)", "shoulderW": 0.175, "height": 1.76,
        "torso": {"color": "1b2742", "details": [{"type": "placket", "color": "121a2e"}, {"type": "buttons", "color": "f0ce60"},
                                                 {"type": "collar", "color": "121a2e"}, {"type": "tabs", "color": "f0ce60"},
                                                 {"type": "belt", "color": "18161a", "buckle": "f0ce60"}]},
        "hat": {"type": "officer", "color": "1b2742"}, "extras": ["glasses"], "shoes": "18161a",
        "face": {"nose": True, "age": 2},
    },
    "kaiser": {
        "name": "Kaiser Wilhelm I (1872)", "shoulderW": 0.185, "height": 1.78,
        "torso": {"color": "1c221e", "details": [{"type": "placket", "color": "a8201e"}, {"type": "buttons", "color": "c8a440"},
                                                 {"type": "collar", "color": "a8201e"}, {"type": "epaulettes", "color": "dfc46c"},
                                                 {"type": "medals"}, {"type": "belt", "color": "181614", "buckle": "d8b44c"}]},
        "hair": {"style": "sides", "color": "4a3a2c"}, "shoes": "181412",
        "face": {"nose": True, "age": 2, "mustache": True, "muttonchops": True, "facial_hair_color": "5a4636"},
    },
    # ---------- The Man Who Sold the Eiffel Tower (1925) ----------
    "lustig": {
        "name": "Victor Lustig (1925)", "shoulderW": 0.165, "height": 1.78,
        "torso": {"color": "242030", "pattern": "pinstripe", "pattern_color": "48425c",
                  "details": [{"type": "panel", "color": "f4f2ec", "width": 0.36, "y0": 0.54},
                              {"type": "bowtie", "color": "b8242c"}, {"type": "buttons", "color": "18161c", "y0": 0.14, "y1": 0.44}]},
        "hat": {"type": "officer", "color": "1c1a24"}, "shoes": "18161c",
        "face": {"nose": True, "mustache": True, "facial_hair_color": "2a201c"},
    },
    "poisson": {
        "name": "Andre Poisson (1925)", "shoulderW": 0.16, "height": 1.70,
        "torso": {"color": "6b4e34", "pattern": "plaid", "pattern_color": "463220",
                  "details": [{"type": "panel", "color": "f4efe4", "width": 0.38, "y0": 0.56},
                              {"type": "bowtie", "color": "2c4868"}, {"type": "buttons", "color": "322216", "y0": 0.14, "y1": 0.44}]},
        "hair": {"style": "short", "color": "4e3622"}, "extras": ["glasses"], "shoes": "2c1e14",
        "face": {"nose": True, "blush": True},
    },
    "dealer_a": {
        "name": "Scrap Dealer A", "shoulderW": 0.17, "height": 1.74,
        "torso": {"color": "2e3a36", "pattern": "pinstripe", "pattern_color": "4a5c56",
                  "details": [{"type": "panel", "color": "f0eee8", "width": 0.34, "y0": 0.56},
                              {"type": "bowtie", "color": "1e2422"}]},
        "hair": {"style": "sides", "color": "7a7670"}, "shoes": "1a1a1a",
        "face": {"nose": True, "age": 2, "mustache": True, "facial_hair_color": "6a6660"},
    },
    "dealer_b": {
        "name": "Scrap Dealer B", "shoulderW": 0.165, "height": 1.76,
        "torso": {"color": "283448",
                  "details": [{"type": "panel", "color": "f0eee8", "width": 0.36, "y0": 0.56},
                              {"type": "bowtie", "color": "8a3028"}]},
        "hair": {"style": "bowl", "color": "2c241e"}, "extras": ["glasses"], "shoes": "1a181e",
        "face": {"nose": True},
    },
}
