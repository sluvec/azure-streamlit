# Sales Analytics Dashboard - Streamlit Demo

Profesjonalny dashboard analityczny zbudowany w Streamlit z przykładowymi danymi sprzedażowymi.

## Funkcje

- 📊 Interaktywne wykresy i wizualizacje (Plotly)
- 🔍 Zaawansowane filtry (data, region, kategoria, produkt)
- 📈 Metryki KPI w czasie rzeczywistym
- 🌍 Analiza regionalna
- 📦 Analiza produktów i kategorii
- 📋 Szczegółowe tabele danych z opcją eksportu
- 🎨 Responsywny i profesjonalny design

## Instalacja

1. Zainstaluj wymagane pakiety:
```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
streamlit run app.py
```

Dashboard będzie dostępny pod adresem: `http://localhost:8501`

## Dane Demo

Dashboard używa wygenerowanych przykładowych danych sprzedażowych obejmujących:
- 5000 transakcji
- 10 produktów z różnych kategorii
- 5 regionów geograficznych
- Dane z ostatnich 12 miesięcy

## Struktura Projektu

```
azure_streamlit/
├── app.py              # Główna aplikacja Streamlit
├── requirements.txt    # Zależności projektu
└── README.md          # Dokumentacja
```

## Deployment

Dashboard jest wdrażany automatycznie na Azure App Service przez GitHub Actions.

**🔗 Live App**: https://azure-streamlit-dashboard.azurewebsites.net

### Dokumentacja Deployment

- **[DEPLOYMENT_REPORT.md](DEPLOYMENT_REPORT.md)** - Szczegółowy raport z procesu wdrożenia, napotkanych problemów i rozwiązań
- **[WORKFLOW_TEMPLATE.md](WORKFLOW_TEMPLATE.md)** - Kompletny szablon i instrukcje do wdrażania podobnych projektów

### Automatyczne Wdrażanie

Każdy push do gałęzi `main` automatycznie uruchamia deployment do Azure:
1. GitHub Actions wykonuje workflow
2. Kod jest pakowany do ZIP
3. Deployment do Azure App Service (async)
4. Aplikacja dostępna w ciągu kilku minut

### Platformy (alternatywy)
- Streamlit Cloud
- Azure App Service ✅ (obecnie używane)
- Heroku
- Docker

## Technologie

- **Streamlit** - Framework do dashboardów
- **Plotly** - Interaktywne wykresy
- **Pandas** - Przetwarzanie danych
- **NumPy** - Obliczenia numeryczne
