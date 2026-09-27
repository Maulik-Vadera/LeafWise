"""Reviewed, non-chemical first steps; model labels never generate treatment text."""
import re

SOURCES = {
    "spots": {"title": "UMN Extension · Tomato leaf spots", "url": "https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/yard-and-garden-problems/tomato-leaf-spot-diseases"},
    "early": {"title": "Maryland Extension · Early blight", "url": "https://www.extension.umd.edu/resource/early-blight-tomatoes"},
    "late": {"title": "UMN Extension · Late blight", "url": "https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/late-blight"},
    "bacterial": {"title": "UMN Extension · Bacterial spot", "url": "https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/bacterial-spot-of-tomato-and-pepper"},
    "mold": {"title": "UMN Extension · Leaf mold", "url": "https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/tomato-leaf-mold"},
    "septoria": {"title": "Maryland Extension · Septoria leaf spot", "url": "https://www.extension.umd.edu/resource/septoria-leaf-spot-tomatoes"},
    "mites": {"title": "UMN Extension · Spider mites", "url": "https://extension.umn.edu/garden-and-home/yard-and-garden/yard-and-garden-insects/spider-mites"},
    "virus": {"title": "UMN Extension · Tomato viruses", "url": "https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/tomato-viruses"},
    "curl": {"title": "UC IPM · Tomato yellow leaf curl", "url": "https://ipm.ucanr.edu/agriculture/tomato/tomato-yellow-leaf-curl/"},
    "grow": {"title": "UMN Extension · Growing tomatoes", "url": "https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/growing-tomatoes"},
    "kvk": {"title": "ICAR · Krishi Vigyan Kendras", "url": "https://www.icar.gov.in/en/krishi-vigyan-kendras-kvks"},
    "dataset": {"title": "PlantVillage · Dataset and label scope", "url": "https://github.com/spMohanty/PlantVillage-Dataset"},
}

# Species names here describe the crop category, not an independent taxonomy model.
CROPS = {
    "Apple": ("Apple", "Malus domestica", "Tree"),
    "Blueberry": ("Blueberry", "Vaccinium spp.", "Shrub"),
    "Cherry_(including_sour)": ("Cherry", "Prunus spp.", "Tree"),
    "Corn_(maize)": ("Maize", "Zea mays", "Cereal grass"),
    "Grape": ("Grape", "Vitis spp.", "Vine"),
    "Orange": ("Orange", "Citrus spp.", "Tree"),
    "Peach": ("Peach", "Prunus persica", "Tree"),
    "Pepper,_bell": ("Bell pepper", "Capsicum annuum", "Vegetable crop"),
    "Potato": ("Potato", "Solanum tuberosum", "Tuber crop"),
    "Raspberry": ("Raspberry", "Rubus spp.", "Shrub"),
    "Soybean": ("Soybean", "Glycine max", "Legume"),
    "Squash": ("Squash", "Cucurbita spp.", "Vine"),
    "Strawberry": ("Strawberry", "Fragaria × ananassa", "Herbaceous crop"),
    "Tomato": ("Tomato", "Solanum lycopersicum", "Vegetable crop"),
}

LABELS = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot", "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight", "Corn_(maize)___healthy", "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy", "Potato___Early_blight",
    "Potato___Late_blight", "Potato___healthy", "Raspberry___healthy", "Soybean___healthy",
    "Squash___Powdery_mildew", "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot", "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus", "Tomato___healthy",
]

def normalized(label):
    return re.sub(r"[^a-z0-9]", "", label.lower())

ALIASES = {normalized(label): label for label in LABELS}

def canonical(label):
    try:
        return ALIASES[normalized(label)]
    except KeyError:
        raise ValueError(f"Unknown model label: {label!r}. Add a reviewed catalog entry first.") from None

GUIDES = {
    "healthy": {
        "name": "No listed disease pattern",
        "summary": "This class resembles the model's healthy examples. It does not rule out early infection, root problems, nutrient stress or diseases outside the model.",
        "look_for": ["Check new growth and the undersides of several leaves.", "Compare the plant with nearby plants of the same crop."],
        "steps": ["Keep a dated photo and check for changes.", "If growth is poor or symptoms continue, arrange a field assessment even when the photo looks healthy."],
        "urgency": "monitor", "sources": ["grow"],
    },
    "Bacterial_spot": {
        "name": "Bacterial spot",
        "summary": "Small dark spots can merge and damage leaves. Similar-looking fungal spots need to be ruled out.",
        "look_for": ["Small dark lesions, sometimes with yellow tissue around them.", "Check fruit and several plants for related spotting."],
        "steps": ["Keep irrigation directed at the soil to limit splash.", "Avoid handling plants while foliage is wet.", "Have a local crop adviser confirm the cause; use clean planting material for the next crop."],
        "urgency": "review", "sources": ["bacterial"],
    },
    "Early_blight": {
        "name": "Early blight",
        "summary": "An early-blight-like pattern can include brown lesions with concentric rings. One leaf is not enough to confirm the pathogen.",
        "look_for": ["Target-like rings within brown spots.", "Older or lower leaves affected before younger growth."],
        "steps": ["Reduce splashing soil onto leaves when watering.", "Maintain suitable spacing and support to improve airflow.", "Record which leaves are affected and ask a crop adviser to confirm."],
        "urgency": "review", "sources": ["early"],
    },
    "Late_blight": {
        "name": "Late blight",
        "summary": "Late blight can progress rapidly in tomato and potato. Suspected cases need prompt local assessment.",
        "look_for": ["Expanding irregular brown areas, sometimes with a pale edge.", "Related dark lesions on stems or fruit; symptoms worsening during damp weather."],
        "steps": ["Contact a local crop adviser promptly if spots are spreading.", "Keep foliage dry where practical and avoid moving suspect planting material.", "Photograph the whole plant, stem and nearby plants for the adviser."],
        "urgency": "prompt", "sources": ["late"],
    },
    "Leaf_Mold": {
        "name": "Leaf mold",
        "summary": "Tomato leaf mold is associated with humid growing conditions, particularly in protected cultivation.",
        "look_for": ["Pale or yellow patches on the upper surface.", "Olive-brown growth beneath corresponding patches."],
        "steps": ["Improve ventilation and avoid persistent leaf wetness.", "Check both sides of leaves and record how many plants are affected.", "Ask an adviser to distinguish mold from other leaf spots."],
        "urgency": "review", "sources": ["mold"],
    },
    "Septoria_leaf_spot": {
        "name": "Septoria leaf spot",
        "summary": "Many small spots can resemble Septoria, but bacterial spot and early blight can look similar.",
        "look_for": ["Small circular lesions with pale centres and darker borders.", "Numerous spots on lower leaves."],
        "steps": ["Limit water splash and wet foliage.", "Support plants to improve airflow.", "Keep a close photo for confirmation by a crop adviser."],
        "urgency": "review", "sources": ["septoria"],
    },
    "Spider_mites Two-spotted_spider_mite": {
        "name": "Spider-mite-like damage",
        "summary": "Feeding can leave fine pale stippling. A leaf classifier cannot confirm the presence of living mites.",
        "look_for": ["Tiny pale dots, bronzing or fine webbing.", "Inspect the underside with a magnifying lens."],
        "steps": ["Check nearby plants and note where symptoms began.", "Avoid letting the crop become water-stressed.", "Ask an adviser to confirm mites before choosing a management plan."],
        "urgency": "review", "sources": ["mites"],
    },
    "Target_Spot": {
        "name": "Target-spot-like pattern",
        "summary": "The classifier includes target spot, but overlapping spot patterns require field confirmation. A dedicated local care protocol is not included.",
        "look_for": ["Photograph several lesions at close range.", "Check whether stems and fruit are also affected."],
        "steps": ["Record progression and growing conditions.", "Take the photos to a local plant clinic or KVK for diagnosis."],
        "urgency": "review", "sources": ["dataset", "kvk"],
    },
    "Tomato_Yellow_Leaf_Curl_Virus": {
        "name": "Yellow-leaf-curl-like symptoms",
        "summary": "Yellowing, curled new leaves and stunting may fit this virus class. Other viruses and non-infectious stress can mimic it.",
        "look_for": ["Small, curled young leaves with yellow margins.", "Stunted growth and whiteflies around the plant."],
        "steps": ["Have the crop checked for both virus symptoms and whiteflies.", "Avoid moving suspect seedlings to other plots.", "Discuss clean planting material and suitable resistant varieties with an adviser."],
        "urgency": "prompt", "sources": ["curl"],
    },
    "Tomato_mosaic_virus": {
        "name": "Mosaic-virus-like symptoms",
        "summary": "Patchy light and dark areas or distorted leaves can fit mosaic symptoms. Laboratory testing may be needed to identify a virus.",
        "look_for": ["Uneven pale and dark-green mottling.", "Distorted leaves or reduced growth."],
        "steps": ["Avoid handling healthy plants immediately after suspect plants.", "Keep tools and hands clean between plants.", "Seek confirmation before removing plants or changing crop management."],
        "urgency": "review", "sources": ["virus"],
    },
}

GENERAL = {
    "summary": "Capture the whole plant and both sides of an affected leaf. Similar symptoms can come from disease, insects, watering or nutrient problems.",
    "look_for": ["Is the problem spreading?", "Are older or younger leaves affected first?"],
    "steps": ["Keep dated photos and note recent rain or watering changes.", "Ask a local KVK or plant clinic to inspect worsening symptoms."],
    "urgency": "review", "sources": ["kvk"],
}

def entry(label):
    label = canonical(label)
    crop, condition = label.split("___", 1)
    name, scientific, kind = CROPS[crop]
    guide = dict(GUIDES.get(condition, {**GENERAL, "name": condition.replace("_", " ")}))
    # Early blight's linked care article is tomato-specific. Keep potato guidance observational.
    if crop == "Potato" and condition == "Early_blight":
        guide = {**GENERAL, "name": "Early-blight-like pattern",
                 "summary": "This class represents potato early blight. Confirm the cause locally; this app does not include a potato-specific treatment protocol."}
    return {"id": label, "crop_id": crop, "crop": name, "scientific_name": scientific,
            "plant_type": kind, "condition": condition, "healthy": condition == "healthy",
            **guide, "sources": [SOURCES[s] for s in guide["sources"]], "reviewed": "2026-09-26"}

def generic_guide():
    return {**GENERAL, "name": "Gather a little more evidence", "sources": [SOURCES["kvk"]]}
