#!/usr/bin/env python3
"""
合成採購資料生成器 (Synthetic Procurement Text Generator)

依據 GHG Protocol Scope 3 類別與常見採購情境生成結構化採購描述

參考文獻：
- Jain et al. (2023) - Scope 3 LLM 研究
- 金融 NLP 與 ESG NLP 研究中的合成資料方法
"""

import random
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class ProcurementTemplate:
    """採購模板結構"""
    category: int  # GHG Protocol Category (1-8 for upstream)
    scenario: str  # 情境：raw_materials, logistics, equipment, services, energy, waste, travel, commute, leased_assets
    industry: str  # 產業別
    item_type: str  # 物料類型
    templates_en: List[str]  # 英文模板
    templates_zh: List[str]  # 中文模板
    amount_range: tuple  # 金額區間 (min, max)
    typical_unit: str  # 典型單位


class SyntheticProcurementGenerator:
    """合成採購資料生成器"""

    def __init__(self):
        """初始化生成器"""
        self.templates = self._load_templates()

    def _load_templates(self) -> List[ProcurementTemplate]:
        """載入採購模板"""

        templates = [
            # ========== Category 1: 購買商品/服務 ==========

            # 1. 原料採購 (Raw Materials)
            ProcurementTemplate(
                category=1,
                scenario="raw_materials",
                industry="Manufacturing",
                item_type="Metal",
                templates_en=[
                    "Purchase of {quantity} {unit} of {material} for manufacturing use",
                    "Procurement of {material} ({quantity} {unit}) for production line",
                    "{material} raw material supply - {quantity} {unit}",
                    "Order {quantity} {unit} of {material} for Q{quarter} production",
                ],
                templates_zh=[
                    "採購 {quantity} {unit} {material}用於製造",
                    "購買 {material} {quantity} {unit} 供生產使用",
                    "{material}原料採購 - {quantity} {unit}",
                ],
                amount_range=(10000, 5000000),
                typical_unit="kg"
            ),

            ProcurementTemplate(
                category=1,
                scenario="raw_materials",
                industry="Manufacturing",
                item_type="Chemical",
                templates_en=[
                    "Purchase of {material} solvent - {quantity} {unit}",
                    "{quantity} {unit} of {material} for chemical processing",
                    "Industrial {material} supply contract ({quantity} {unit})",
                ],
                templates_zh=[
                    "採購 {material} 溶劑 {quantity} {unit}",
                    "購買工業用 {material} {quantity} {unit}",
                ],
                amount_range=(5000, 2000000),
                typical_unit="liters"
            ),

            ProcurementTemplate(
                category=1,
                scenario="raw_materials",
                industry="Food & Beverage",
                item_type="Agricultural",
                templates_en=[
                    "Purchase of {quantity} {unit} of {material} for food production",
                    "{material} ingredient procurement - {quantity} {unit}",
                    "Order organic {material} ({quantity} {unit}) from certified supplier",
                ],
                templates_zh=[
                    "採購 {quantity} {unit} {material}作為食品原料",
                    "購買有機 {material} {quantity} {unit}",
                ],
                amount_range=(8000, 3000000),
                typical_unit="tons"
            ),

            ProcurementTemplate(
                category=1,
                scenario="raw_materials",
                industry="Electronics",
                item_type="Electronic Components",
                templates_en=[
                    "Purchase of {quantity} units of {material} for assembly",
                    "{material} component procurement ({quantity} pcs)",
                    "Order {quantity} {material} for production batch",
                ],
                templates_zh=[
                    "採購 {quantity} 個 {material}用於組裝",
                    "購買 {material} 元件 {quantity} 個",
                ],
                amount_range=(15000, 8000000),
                typical_unit="units"
            ),

            # 2. 物流運輸 (Logistics) - 現改為 Category 4
            ProcurementTemplate(
                category=4,
                scenario="logistics",
                industry="Logistics",
                item_type="Freight",
                templates_en=[
                    "Monthly freight service for {route} distribution",
                    "{service_type} transportation service - {route}",
                    "Contract for {quantity} shipments via {service_type}",
                    "Logistics service for {route} corridor ({period})",
                    "Third-party freight forwarding services ({route})",
                ],
                templates_zh=[
                    "{route}區域配送月度運輸服務",
                    "{service_type}運輸服務 - {route}",
                    "物流服務合約 - {route}線 ({period})",
                    "委外物流配送服務 ({route})",
                ],
                amount_range=(20000, 5000000),
                typical_unit="shipments"
            ),

            ProcurementTemplate(
                category=4,
                scenario="logistics",
                industry="Logistics",
                item_type="Warehousing",
                templates_en=[
                    "Warehouse storage service ({quantity} sqm for {period})",
                    "Third-party warehousing at {location} - {quantity} sqm",
                    "Cold storage rental ({quantity} cbm) for {period}",
                ],
                templates_zh=[
                    "倉儲服務 ({quantity} 平方公尺，{period})",
                    "{location}第三方倉儲 - {quantity} 坪",
                    "冷凍倉儲租賃 ({quantity} 立方公尺)",
                ],
                amount_range=(15000, 3000000),
                typical_unit="sqm"
            ),

            # 3. 一般服務 (Services)
            ProcurementTemplate(
                category=1,
                scenario="services",
                industry="Professional Services",
                item_type="Consulting",
                templates_en=[
                    "{service_type} consulting services for {period}",
                    "Professional advisory service - {service_type}",
                    "Engagement of {service_type} consultant ({duration} months)",
                ],
                templates_zh=[
                    "{service_type}諮詢服務 ({period})",
                    "聘請 {service_type}顧問 ({duration} 個月)",
                    "{service_type}專業服務合約",
                ],
                amount_range=(50000, 2000000),
                typical_unit="project"
            ),

            ProcurementTemplate(
                category=1,
                scenario="services",
                industry="IT Services",
                item_type="Software",
                templates_en=[
                    "{software} software subscription ({quantity} licenses for {period})",
                    "Cloud {service_type} service - {period} contract",
                    "SaaS subscription for {software} ({quantity} users)",
                ],
                templates_zh=[
                    "{software}軟體訂閱 ({quantity} 授權，{period})",
                    "雲端 {service_type}服務 - {period}合約",
                    "{software} SaaS 訂閱 ({quantity} 使用者)",
                ],
                amount_range=(10000, 1000000),
                typical_unit="licenses"
            ),

            ProcurementTemplate(
                category=1,
                scenario="services",
                industry="Facility Management",
                item_type="Maintenance",
                templates_en=[
                    "Facility maintenance service for {period}",
                    "Building management service ({location}, {duration} months)",
                    "Cleaning and maintenance contract for office premises",
                ],
                templates_zh=[
                    "設施維護服務 ({period})",
                    "{location}大樓管理服務 ({duration} 個月)",
                    "辦公場所清潔維護合約",
                ],
                amount_range=(30000, 1500000),
                typical_unit="contract"
            ),

            # ========== Category 2: 資本財 ==========

            # 1. 製造設備 (Manufacturing Equipment)
            ProcurementTemplate(
                category=2,
                scenario="equipment",
                industry="Manufacturing",
                item_type="Machinery",
                templates_en=[
                    "Purchase of {equipment} for production facility",
                    "{equipment} acquisition - {specification}",
                    "Industrial {equipment} ({quantity} units) with installation",
                    "Procurement of automated {equipment} system",
                ],
                templates_zh=[
                    "採購 {equipment}用於生產設施",
                    "購置 {equipment} - {specification}",
                    "工業用 {equipment} ({quantity} 台) 含安裝",
                ],
                amount_range=(500000, 50000000),
                typical_unit="units"
            ),

            ProcurementTemplate(
                category=2,
                scenario="equipment",
                industry="Manufacturing",
                item_type="Production Line",
                templates_en=[
                    "Complete {product} production line installation",
                    "{product} manufacturing line ({capacity} units/day capacity)",
                    "Automated assembly line for {product}",
                ],
                templates_zh=[
                    "完整 {product}生產線安裝",
                    "{product}製造產線 (產能 {capacity} 件/日)",
                    "{product}自動化組裝線",
                ],
                amount_range=(5000000, 100000000),
                typical_unit="line"
            ),

            # 2. IT 設備 (IT Equipment)
            ProcurementTemplate(
                category=2,
                scenario="equipment",
                industry="IT Infrastructure",
                item_type="Hardware",
                templates_en=[
                    "Purchase of {quantity} {equipment} for data center",
                    "{equipment} procurement ({specification})",
                    "IT infrastructure upgrade - {equipment} ({quantity} units)",
                ],
                templates_zh=[
                    "採購 {quantity} 台 {equipment}用於資料中心",
                    "購置 {equipment} ({specification})",
                    "IT 基礎設施升級 - {equipment} ({quantity} 台)",
                ],
                amount_range=(200000, 10000000),
                typical_unit="units"
            ),

            # 3. 運輸設備 (Transportation Equipment)
            ProcurementTemplate(
                category=2,
                scenario="equipment",
                industry="Transportation",
                item_type="Vehicle",
                templates_en=[
                    "Fleet procurement - {quantity} {vehicle_type}",
                    "Purchase of {quantity} {vehicle_type} for logistics operations",
                    "{vehicle_type} acquisition ({specification})",
                ],
                templates_zh=[
                    "車隊採購 - {quantity} 輛 {vehicle_type}",
                    "購買 {quantity} 輛 {vehicle_type}用於物流運營",
                    "{vehicle_type}採購 ({specification})",
                ],
                amount_range=(800000, 30000000),
                typical_unit="vehicles"
            ),

            # 4. 建築設施 (Building & Facilities)
            ProcurementTemplate(
                category=2,
                scenario="equipment",
                industry="Real Estate",
                item_type="Building",
                templates_en=[
                    "Construction of {facility_type} ({area} sqm)",
                    "New {facility_type} development project",
                    "{facility_type} building contract ({location})",
                ],
                templates_zh=[
                    "建造 {facility_type} ({area} 平方公尺)",
                    "新建 {facility_type}開發專案",
                    "{facility_type}建築合約 ({location})",
                ],
                amount_range=(10000000, 500000000),
                typical_unit="sqm"
            ),

            ProcurementTemplate(
                category=2,
                scenario="equipment",
                industry="Energy",
                item_type="Power Generation",
                templates_en=[
                    "Solar panel installation ({capacity} kW capacity)",
                    "{equipment} power generation system - {capacity} MW",
                    "Renewable energy facility construction ({capacity} MW)",
                ],
                templates_zh=[
                    "太陽能板安裝 (容量 {capacity} kW)",
                    "{equipment}發電系統 - {capacity} MW",
                    "再生能源設施建設 ({capacity} MW)",
                ],
                amount_range=(3000000, 200000000),
                typical_unit="kW"
            ),

            # ========== Category 3: 燃料與能源相關活動 ==========

            ProcurementTemplate(
                category=3,
                scenario="energy",
                industry="Utilities",
                item_type="Electricity",
                templates_en=[
                    "Electricity purchase ({quantity} kWh) - {supplier}",
                    "Power supply contract for {period} ({quantity} kWh)",
                    "Renewable electricity procurement ({quantity} MWh)",
                    "Grid electricity for {location} facility ({period})",
                ],
                templates_zh=[
                    "採購電力 {quantity} 度（{supplier}）",
                    "電力供應合約 ({period}，{quantity} kWh)",
                    "再生能源電力採購 ({quantity} MWh)",
                    "{location}設施用電 ({period})",
                ],
                amount_range=(50000, 5000000),
                typical_unit="kWh"
            ),

            ProcurementTemplate(
                category=3,
                scenario="energy",
                industry="Utilities",
                item_type="Fuel",
                templates_en=[
                    "Diesel fuel procurement ({quantity} liters)",
                    "Natural gas supply contract ({quantity} cubic meters)",
                    "Gasoline purchase for fleet operations ({quantity} liters)",
                    "LPG supply for {location} ({period})",
                ],
                templates_zh=[
                    "柴油燃料採購 ({quantity} 公升)",
                    "天然氣供應合約 ({quantity} 立方公尺)",
                    "汽油採購供車隊使用 ({quantity} 公升)",
                    "{location}液化石油氣供應 ({period})",
                ],
                amount_range=(30000, 3000000),
                typical_unit="liters"
            ),

            # ========== Category 5: 營運產生的廢棄物 ==========

            ProcurementTemplate(
                category=5,
                scenario="waste",
                industry="Environmental Services",
                item_type="Waste Disposal",
                templates_en=[
                    "Industrial waste disposal service ({period})",
                    "Hazardous waste treatment contract ({quantity} tons)",
                    "General waste collection service for {location}",
                    "Recycling service contract ({period})",
                ],
                templates_zh=[
                    "事業廢棄物清運處理 ({period})",
                    "有害廢棄物處理合約 ({quantity} 噸)",
                    "{location}一般廢棄物清運服務",
                    "資源回收處理服務合約 ({period})",
                ],
                amount_range=(20000, 1500000),
                typical_unit="contract"
            ),

            # ========== Category 6: 商務差旅 ==========

            ProcurementTemplate(
                category=6,
                scenario="travel",
                industry="Business Services",
                item_type="Air Travel",
                templates_en=[
                    "Business class flight tickets to {destination}",
                    "Employee business travel ({quantity} trips, {destination})",
                    "International air travel ({route}, {period})",
                    "Corporate travel package for {department} ({period})",
                ],
                templates_zh=[
                    "商務艙機票至{destination}",
                    "員工商務差旅 ({quantity} 趟，{destination})",
                    "國際航空差旅 ({route}，{period})",
                    "{department}部門商務旅遊套裝 ({period})",
                ],
                amount_range=(30000, 2000000),
                typical_unit="trips"
            ),

            ProcurementTemplate(
                category=6,
                scenario="travel",
                industry="Business Services",
                item_type="Accommodation",
                templates_en=[
                    "Hotel accommodation for {department} ({period})",
                    "Corporate lodging contract - {destination}",
                    "Business trip hotel bookings ({quantity} nights)",
                ],
                templates_zh=[
                    "{department}部門住宿費用 ({period})",
                    "企業住宿合約 - {destination}",
                    "商務差旅住宿預訂 ({quantity} 晚)",
                ],
                amount_range=(15000, 800000),
                typical_unit="nights"
            ),

            ProcurementTemplate(
                category=6,
                scenario="travel",
                industry="Business Services",
                item_type="Ground Transportation",
                templates_en=[
                    "Rental car service for business travel ({period})",
                    "Corporate taxi/rideshare account ({period})",
                    "Airport shuttle service contract",
                ],
                templates_zh=[
                    "商務差旅租車服務 ({period})",
                    "企業計程車/叫車帳號 ({period})",
                    "機場接駁服務合約",
                ],
                amount_range=(10000, 500000),
                typical_unit="contract"
            ),

            # ========== Category 7: 員工通勤 ==========

            ProcurementTemplate(
                category=7,
                scenario="commute",
                industry="HR Services",
                item_type="Commute Allowance",
                templates_en=[
                    "Employee transportation allowance ({period})",
                    "Commute subsidy for {quantity} employees",
                    "Public transport pass program ({period})",
                    "Employee parking fee reimbursement ({period})",
                ],
                templates_zh=[
                    "員工交通津貼補助 ({period})",
                    "{quantity} 名員工通勤補貼",
                    "大眾運輸月票計畫 ({period})",
                    "員工停車費報支 ({period})",
                ],
                amount_range=(50000, 2000000),
                typical_unit="employees"
            ),

            ProcurementTemplate(
                category=7,
                scenario="commute",
                industry="HR Services",
                item_type="Shuttle Service",
                templates_en=[
                    "Company shuttle bus service ({period})",
                    "Employee transportation contract - {route}",
                    "Commuter van leasing ({quantity} vehicles)",
                ],
                templates_zh=[
                    "公司交通車服務 ({period})",
                    "員工接駁車合約 - {route}",
                    "通勤廂型車租賃 ({quantity} 輛)",
                ],
                amount_range=(80000, 1500000),
                typical_unit="vehicles"
            ),

            # ========== Category 8: 上游租賃資產 ==========

            ProcurementTemplate(
                category=8,
                scenario="leased_assets",
                industry="Real Estate",
                item_type="Office Lease",
                templates_en=[
                    "Office space leasing ({area} sqm, {location})",
                    "Commercial property rental contract ({period})",
                    "Co-working space membership ({quantity} seats)",
                    "Warehouse leasing at {location} ({area} sqm)",
                ],
                templates_zh=[
                    "辦公室租賃 ({area} 坪，{location})",
                    "商業不動產租賃合約 ({period})",
                    "共同工作空間會員 ({quantity} 個座位)",
                    "{location}倉庫租賃 ({area} 平方公尺)",
                ],
                amount_range=(100000, 10000000),
                typical_unit="sqm"
            ),

            ProcurementTemplate(
                category=8,
                scenario="leased_assets",
                industry="Equipment Services",
                item_type="Equipment Lease",
                templates_en=[
                    "Equipment leasing ({equipment}, {duration} months)",
                    "IT hardware rental contract ({quantity} units)",
                    "Industrial machinery lease ({period})",
                    "Office equipment rental ({period})",
                ],
                templates_zh=[
                    "設備租賃 ({equipment}，{duration} 個月)",
                    "IT 硬體租賃合約 ({quantity} 台)",
                    "工業機械租賃 ({period})",
                    "辦公設備租賃 ({period})",
                ],
                amount_range=(30000, 3000000),
                typical_unit="units"
            ),
        ]

        return templates

    def generate(self,
                 n_samples: int = 1000,
                 language: str = "en",
                 categories: Optional[List[int]] = None,
                 scenarios: Optional[List[str]] = None,
                 seed: int = 42) -> pd.DataFrame:
        """
        生成合成採購資料

        Args:
            n_samples: 生成樣本數
            language: 語言 ("en" 或 "zh")
            categories: 指定 GHG 類別 (None 表示全部)
            scenarios: 指定情境 (None 表示全部)
            seed: 隨機種子

        Returns:
            DataFrame with columns: description, category, scenario, industry, item_type, amount
        """
        random.seed(seed)

        # 篩選模板
        filtered_templates = self.templates
        if categories:
            filtered_templates = [t for t in filtered_templates if t.category in categories]
        if scenarios:
            filtered_templates = [t for t in filtered_templates if t.scenario in scenarios]

        if not filtered_templates:
            raise ValueError("No templates match the specified filters")

        # 定義填充值
        materials = {
            "Metal": ["aluminum alloy", "steel sheets", "copper wire", "stainless steel", "titanium"],
            "Chemical": ["acetone", "ethanol", "sulfuric acid", "sodium hydroxide", "toluene"],
            "Agricultural": ["wheat", "soybeans", "corn", "rice", "sugar"],
            "Electronic Components": ["PCB boards", "resistors", "capacitors", "microchips", "LED modules"],
        }

        materials_zh = {
            "Metal": ["鋁合金", "鋼板", "銅線", "不鏽鋼", "鈦金屬"],
            "Chemical": ["丙酮", "乙醇", "硫酸", "氫氧化鈉", "甲苯"],
            "Agricultural": ["小麥", "大豆", "玉米", "稻米", "糖"],
            "Electronic Components": ["PCB 電路板", "電阻", "電容", "微晶片", "LED 模組"],
        }

        routes = ["North-South", "East-West", "regional", "cross-border", "urban"]
        routes_zh = ["南北", "東西", "區域", "跨境", "市區"]

        service_types = ["management", "IT", "sustainability", "financial", "legal"]
        service_types_zh = ["管理", "IT", "永續", "財務", "法律"]

        locations = ["headquarters", "regional office", "warehouse", "factory", "branch"]
        locations_zh = ["總部", "區域辦公室", "倉庫", "工廠", "分公司"]

        equipment_types = ["CNC machine", "injection molding machine", "conveyor system",
                          "robotic arm", "packaging machine"]
        equipment_types_zh = ["CNC 機床", "射出成型機", "輸送系統", "機械手臂", "包裝機"]

        vehicle_types = ["delivery trucks", "electric vans", "forklifts", "cargo vehicles"]
        vehicle_types_zh = ["貨車", "電動廂型車", "堆高機", "載貨車輛"]

        facility_types = ["warehouse", "office building", "manufacturing plant", "distribution center"]
        facility_types_zh = ["倉庫", "辦公大樓", "製造廠", "配送中心"]

        suppliers = ["Taiwan Power Company", "Local Utility", "Renewable Energy Provider", "National Grid"]
        suppliers_zh = ["台電", "地方公用事業", "再生能源供應商", "國家電網"]

        destinations = ["Tokyo", "Singapore", "Shanghai", "San Francisco", "London", "Seoul"]
        destinations_zh = ["東京", "新加坡", "上海", "舊金山", "倫敦", "首爾"]

        departments = ["sales team", "management", "engineering", "operations", "R&D"]
        departments_zh = ["業務", "管理", "工程", "營運", "研發"]

        # 生成樣本
        samples = []

        for _ in range(n_samples):
            # 隨機選擇模板
            template = random.choice(filtered_templates)

            # 選擇語言模板
            if language == "zh":
                text_template = random.choice(template.templates_zh)
            else:
                text_template = random.choice(template.templates_en)

            # 準備填充變數
            fill_vars = {
                "quantity": random.randint(10, 10000),
                "unit": template.typical_unit,
                "quarter": random.choice(["Q1", "Q2", "Q3", "Q4"]),
                "period": random.choice(["12 months", "6 months", "annual", "quarterly"]),
                "duration": random.randint(6, 36),
                "capacity": random.randint(100, 10000),
                "area": random.randint(500, 50000),
                "specification": "industrial grade",
            }

            # 根據 item_type 填充材料
            if template.item_type in materials:
                fill_vars["material"] = random.choice(
                    materials_zh[template.item_type] if language == "zh" else materials[template.item_type]
                )

            fill_vars["route"] = random.choice(routes_zh if language == "zh" else routes)
            fill_vars["service_type"] = random.choice(service_types_zh if language == "zh" else service_types)
            fill_vars["location"] = random.choice(locations_zh if language == "zh" else locations)
            fill_vars["equipment"] = random.choice(equipment_types_zh if language == "zh" else equipment_types)
            fill_vars["vehicle_type"] = random.choice(vehicle_types_zh if language == "zh" else vehicle_types)
            fill_vars["facility_type"] = random.choice(facility_types_zh if language == "zh" else facility_types)
            fill_vars["software"] = random.choice(["ERP", "CRM", "Analytics", "Security", "Collaboration"])
            fill_vars["product"] = random.choice(["electronics", "automotive parts", "consumer goods"])
            fill_vars["supplier"] = random.choice(suppliers_zh if language == "zh" else suppliers)
            fill_vars["destination"] = random.choice(destinations_zh if language == "zh" else destinations)
            fill_vars["department"] = random.choice(departments_zh if language == "zh" else departments)

            # 生成描述文字
            try:
                description = text_template.format(**fill_vars)
            except KeyError:
                # 如果某些變數不存在，跳過
                continue

            # 生成金額
            amount = random.uniform(*template.amount_range)

            samples.append({
                "description": description,
                "ghg_category": template.category,
                "scenario": template.scenario,
                "industry": template.industry,
                "item_type": template.item_type,
                "amount": round(amount, 2),
                "language": language
            })

        return pd.DataFrame(samples)

    def generate_balanced_dataset(self,
                                   total_samples: int = 2000,
                                   language: str = "en",
                                   category_ratio: Dict[int, float] = None,
                                   seed: int = 42) -> pd.DataFrame:
        """
        生成平衡的資料集

        Args:
            total_samples: 總樣本數
            language: 語言
            category_ratio: 類別比例，例如：
                {1: 0.35, 2: 0.20, 3: 0.15, 4: 0.10, 5: 0.08, 6: 0.07, 7: 0.03, 8: 0.02}
            seed: 隨機種子

        Returns:
            平衡的資料集
        """
        if category_ratio is None:
            # 預設比例（涵蓋8個類別）
            category_ratio = {
                1: 0.35,  # Purchased goods/services
                2: 0.20,  # Capital goods
                3: 0.15,  # Fuel & energy
                4: 0.10,  # Upstream transportation
                5: 0.08,  # Waste
                6: 0.07,  # Business travel
                7: 0.03,  # Employee commuting
                8: 0.02,  # Upstream leased assets
            }

        dfs = []
        for category, ratio in category_ratio.items():
            n = int(total_samples * ratio)
            if n > 0:  # 只有當樣本數 > 0 才生成
                df = self.generate(
                    n_samples=n,
                    language=language,
                    categories=[category],
                    seed=seed + category  # 每個類別使用不同種子
                )
                dfs.append(df)

        result = pd.concat(dfs, ignore_index=True)

        # 隨機打亂
        result = result.sample(frac=1, random_state=seed).reset_index(drop=True)

        return result


def main():
    """測試生成器"""
    print("=" * 80)
    print("  合成採購資料生成器 v2.0 - 擴充至 8 個 Scope 3 類別")
    print("=" * 80)

    generator = SyntheticProcurementGenerator()

    # 定義類別比例（涵蓋 8 個類別）
    category_ratio = {
        1: 0.35,  # Purchased goods/services
        2: 0.20,  # Capital goods
        3: 0.15,  # Fuel & energy
        4: 0.10,  # Upstream transportation
        5: 0.08,  # Waste
        6: 0.07,  # Business travel
        7: 0.03,  # Employee commuting
        8: 0.02,  # Upstream leased assets
    }

    # 生成英文資料（擴充至 2000 筆）
    print("\n📝 生成英文合成採購資料（涵蓋 8 個 Scope 3 類別）...")
    df_en = generator.generate_balanced_dataset(
        total_samples=2000,
        language="en",
        category_ratio=category_ratio
    )

    print(f"✅ 生成 {len(df_en)} 筆英文資料")
    print(f"\n   Category 分布:")
    for cat in sorted(df_en['ghg_category'].unique()):
        count = (df_en['ghg_category'] == cat).sum()
        pct = count / len(df_en) * 100
        print(f"      Category {cat}: {count:>4} 筆 ({pct:>5.1f}%)")

    print(f"\n   Scenario 分布:")
    for scenario, count in df_en['scenario'].value_counts().items():
        pct = count / len(df_en) * 100
        print(f"      {scenario:20s}: {count:>4} 筆 ({pct:>5.1f}%)")

    # 顯示各類別範例
    category_names = {
        1: "Purchased goods/services",
        2: "Capital goods",
        3: "Fuel & energy",
        4: "Upstream transportation",
        5: "Waste",
        6: "Business travel",
        7: "Employee commuting",
        8: "Upstream leased assets",
    }

    print(f"\n   各類別範例:")
    for cat in sorted(df_en['ghg_category'].unique()):
        cat_df = df_en[df_en['ghg_category'] == cat]
        print(f"\n   Category {cat}: {category_names[cat]}")
        for idx, row in cat_df.head(2).iterrows():
            print(f"      • {row['description']}")

    # 生成中文資料（擴充至 2000 筆）
    print("\n\n📝 生成中文合成採購資料（涵蓋 8 個 Scope 3 類別）...")
    df_zh = generator.generate_balanced_dataset(
        total_samples=2000,
        language="zh",
        category_ratio=category_ratio
    )

    print(f"✅ 生成 {len(df_zh)} 筆中文資料")
    print(f"\n   各類別範例:")
    for cat in sorted(df_zh['ghg_category'].unique()):
        cat_df = df_zh[df_zh['ghg_category'] == cat]
        print(f"\n   Category {cat}: {category_names[cat]}")
        for idx, row in cat_df.head(2).iterrows():
            print(f"      • {row['description']}")

    # 儲存資料
    from pathlib import Path
    output_dir = Path(__file__).parent.parent.parent / "data" / "synthetic"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 儲存擴充版本（v2）
    df_en.to_csv(output_dir / "synthetic_procurement_en_2000_v2.csv", index=False, encoding='utf-8-sig')
    df_zh.to_csv(output_dir / "synthetic_procurement_zh_2000_v2.csv", index=False, encoding='utf-8-sig')

    print(f"\n💾 資料已儲存至: {output_dir}")
    print(f"   • synthetic_procurement_en_2000_v2.csv ({len(df_en)} 筆)")
    print(f"   • synthetic_procurement_zh_2000_v2.csv ({len(df_zh)} 筆)")

    # 統計摘要
    print(f"\n📊 資料集摘要:")
    print(f"   總樣本數: {len(df_en) + len(df_zh):,} 筆")
    print(f"   Scope 3 覆蓋率: 8/15 類別 = 53.3%")
    print(f"   行業數量: {df_en['industry'].nunique()} 個")
    print(f"   產品類型: {df_en['item_type'].nunique()} 種")

    print("\n" + "=" * 80)
    print("  ✅ 測試完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
