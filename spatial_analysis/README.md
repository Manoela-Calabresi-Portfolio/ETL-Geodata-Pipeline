# Stuttgart Mobility & Walkability Analysis Pipeline

## 🎯 Objetivo

Pipeline Python modular para calcular indicadores de mobilidade e caminhabilidade para cada Stadtbezirk de Stuttgart, utilizando dados do pipeline principal quando disponível e coletando dados adicionais específicos.

## 📁 Estrutura do Pipeline

```
spatial_analysis/
├── config/
│   ├── analysis_config.yaml    # Configuração principal
│   ├── kpi_weights.yaml        # Pesos dos indicadores
│   └── stadtbezirke.yaml       # Configuração dos distritos
├── scripts/
│   ├── 1_data_collection.py    # Coleta e processamento de dados
│   ├── 2_kpi_calculation.py    # Cálculo dos indicadores
│   ├── 3_visualization.py      # Mapas e rankings
│   └── utils/
│       ├── osm_collector.py    # Funções OSM específicas
│       ├── gtfs_processor.py   # Processamento GTFS
│       ├── geometry_utils.py   # Utilitários geométricos
│       └── kpi_calculators.py  # Calculadoras de KPIs
├── data/
│   ├── raw/                    # Dados brutos baixados
│   ├── processed/              # Dados processados
│   └── results/                # Resultados finais
└── outputs/
    ├── maps/                   # Mapas gerados
    ├── rankings/               # Rankings e tabelas
    └── reports/                # Relatórios finais
```

## 🔗 Integração com Pipeline Principal

### Dados Reutilizados:
- **Amenities**: `../data_final/stuttgart/processed/amenities_categorized.parquet`
- **PT Stops**: `../data_final/stuttgart/processed/pt_stops_categorized.parquet`
- **Roads**: `../data_final/stuttgart/processed/roads_categorized.parquet`
- **Landuse**: `../data_final/stuttgart/processed/landuse_categorized.parquet`

### Dados Adicionais Necessários:
- **GTFS VVS**: Download direto da MobiData BW
- **Geometrias Stadtbezirke**: Download oficial da prefeitura
- **OSM específico**: Cruzamentos e POIs adicionais via osmnx

## 📊 Indicadores (KPIs)

### 1. Transporte Público
- % população ≤ 300m de parada alta frequência (headway ≤ 15min)
- Nº médio de linhas acessíveis por distrito

### 2. Caminhabilidade
- Densidade de cruzamentos (n/km²)
- % população ≤ 500m de POIs (mercado, escola, parque)

### 3. Áreas Verdes
- % população ≤ 500m de área verde pública

## 🚀 Execução

```bash
# Coleta de dados
python spatial_analysis/scripts/1_data_collection.py

# Cálculo de KPIs
python spatial_analysis/scripts/2_kpi_calculation.py

# Visualização
python spatial_analysis/scripts/3_visualization.py
```

## ⚙️ Configuração

Cada módulo pode ser executado independentemente através de flags:

```bash
# Apenas GTFS
python 1_data_collection.py --gtfs-only

# Apenas OSM
python 1_data_collection.py --osm-only

# Recalcular apenas KPIs de transporte
python 2_kpi_calculation.py --transport-only
```
