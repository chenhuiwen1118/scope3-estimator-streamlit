# GHG Report Gold Standard Source Candidates

This document lists public greenhouse gas inventory / ESG report sources that
can help expand the training and gold-standard pool across industries.

Use these reports as candidate sources first. Only rows with traceable activity
name, factor name, factor value, unit, source, year, boundary, and calculation
result should be promoted to gold-standard records.

## Priority Sources

| Priority | Industry | Candidate source | Source URL | Training value | Gold-standard use |
|---|---|---|---|---|---|
| High | Plastics / industrial wholesale | 嘉澎塑膠 GHG report, 2025 | https://esg.chia.com.tw/ | Has Scope 3 purchased goods, procurement weight, spend, NAICS factor, exchange rate, and calculation narrative. | Good for purchased goods and spend-based Scope 3 examples after manual validation. |
| High | Electronics / semiconductor IC | 松翰科技 2024 greenhouse gas inventory report | https://device.report/m/72a97cd7c918fe41c54115e6d1dbf09da7b290433599cfeb505e25431e2a00fb | Public inventory report with ISO-style quantification and emission-factor references. | Good candidate for electronics activity terms and factor-source mapping. |
| Medium | IC design / semiconductor service | Faraday / 智原科技 TCFD and GHG inventory disclosure | https://www.faraday-tech.com/tw/content/CSR/TCFD | Has multi-year Scope 1, Scope 2, and Scope 3 category data plus local factor-source notes. | Useful for office, outsourced service, fuel and energy, commuting, travel, and waste category classification. |
| Medium | Textile / manufacturing | 台灣百和工業 ESG greenhouse gas inventory | https://esg.paiho.com/environment-detail/GHG-Inventory/ | Discloses Scope 3 category details including purchased goods, capital goods, transport, commute, business travel, and waste. | Useful for ISO category to GHG Protocol category mapping and Scope 3 category training. |
| Medium | PCB / electronics manufacturing | 金像電子 ESG greenhouse gas page | https://www.gce.com.tw/csrresult.html | Has Scope 3 category-level data for purchased goods, capital goods, fuel/energy, transport, waste, travel, commuting. | Useful for category classification; less suitable as item-level factor gold unless detailed tables are found. |
| Medium | Semiconductor packaging/testing | 力成科技 2024 ESG report | https://www.scribd.com/document/944183443/2024-PTI-ESG-Report-zh | Has Scope 3 category-level emissions and verified Scope 1/2 disclosures. | Useful for sector coverage and category labels; item-level factor extraction may be limited. |
| Medium | Precision machinery | 協易機械 ESG carbon emissions management | https://esg.seyi.com/carbon-emissions-management | Discloses inventory approach and factor source version. | Useful for machinery-sector vocabulary and source precedence rules. |
| Medium | Food / feed manufacturing | 福壽實業 GHG inventory disclosure | https://esg.fwusow.com.tw/article_d.php?id=68&lang=tw&tb=4 | Includes Scope 1/2/3 disclosure notes and factor-source references. | Useful for food/feed sector category examples; likely needs additional detail for factor-level gold records. |
| Medium | Nonprofit / multi-site service | 慈濟基金會 GHG inventory disclosure | https://tzuchi-csr.org.tw/ghg-inventory.php?lan=cht | Shows ISO category and GHG Protocol mapping with purchased goods, raw materials, waste, upstream energy, travel, commute, and services. | Useful for service-sector Scope 3 category labeling and bilingual category mapping. |
| Medium | Education / campus | 亞洲大學 ISO 14064-1 page and inventory statements | https://env.asia.edu.tw/zh_tw/ISOOHSASarea/12 | Lists factor sources, GWP sources, and verification files. | Useful for service/campus activity taxonomy and factor-source rules. |
| Medium | Agriculture / government agency | 農業部 2024 greenhouse gas inventory report | https://agrinetzero.moa.gov.tw/zh-TW/News/Detail/1104 | Public agency inventory report for agriculture-sector context. | Useful for public-sector and agriculture activity examples after table extraction. |
| Medium | Government administration | 經濟部 internal greenhouse gas inventory page | https://www.moea.gov.tw/MNS/populace/content/Content2.aspx?menu_id=44746 | Discloses organizational boundary, Scope 1/2 totals, and source basis. | Useful for office/service emission source examples; limited item-level factor detail. |
| Medium | Automotive manufacturing | 裕隆汽車 GHG inventory and emissions management | https://ylesg.yulon-motor.com.tw/environment/greenhouse | Provides automotive-sector GHG disclosure and reduction management context. | Useful for automotive sector vocabulary and supplier-chain context; verify whether item-level factors are available. |
| Medium | Official factor / method source | 環境部氣候變遷署事業溫室氣體排放量資訊平台 | https://ghgregistry.moenv.gov.tw/epa_ghg/Downloads/FileDownloads.aspx?Category=insp | Provides official inventory forms, factor table, industry templates, and inventory guidance. | Use as authoritative factor and method source, not as company-specific gold-standard rows. |
| Medium | Official inventory baseline | 氣候變遷署國家溫室氣體清冊報告 | https://www.cca.gov.tw/information-service/publications/national-ghg-inventory-report/1722.html | Provides national sector-level inventory methodology and official context. | Useful for sector taxonomy and QA rules; not directly procurement-item gold. |
| Low | City / transport / wastewater | 高雄市 greenhouse gas inventory report | Public city disclosure pages and reports | Contains city-level sector tables for transport, industry process, agriculture, and waste/wastewater. | Useful for transport/wastewater/agriculture factor patterns; not directly procurement-item gold. |

## Promotion Rules

A report row can become a gold-standard record only if it includes:

- Activity or procurement item name.
- Correct matched emission-factor name.
- Emission-factor value.
- Factor unit.
- Factor source and version/year.
- Activity data and unit.
- Calculated CO2e result.
- Scope / ISO 14064 category.
- System boundary or calculation boundary.
- Evidence location in the source report.

Rows without enough evidence should remain as training reference, not gold
standard.

## Recommended Next Dataset Targets

To improve sector balance, collect at least 5 to 10 validated rows from each:

- Plastics and rubber products.
- Electronics and semiconductor.
- PCB / electronic components.
- Machinery equipment.
- Food and feed manufacturing.
- Financial / office service.
- Logistics and transportation.
- Education / campus.
- Healthcare / hospital.
- Construction / building materials.
- Waste and wastewater treatment.
- Agriculture / food supply chain.

## Extraction Workflow

1. Collect public reports or pages and record source URL, organization,
   industry, report year, and assurance status.
2. Extract only rows with a traceable activity item, factor, unit, source, and
   calculated result.
3. Normalize the row to the system schema: procurement item, recommended
   emission factor, factor value, factor unit, activity quantity, activity unit,
   CO2e, Scope 3 category, ISO category, geography, year, boundary, source, and
   evidence location.
4. Mark rows as `gold` only after manual validation. Use `training_reference`
   for category-level disclosures or rows missing factor details.
