# Przewodnik Krok po Kroku: Deployment Streamlit na Azure przez GitHub Actions

**Ten przewodnik powstał na podstawie rzeczywistego projektu i zawiera sprawdzone rozwiązania.**

## 🎯 Cel

Wdrożyć aplikację Streamlit na Azure App Service z automatycznym deploymentem przez GitHub Actions, **unikając** typowych problemów.

## ⏱️ Szacowany Czas

- Początkujący: 45-60 minut
- Z doświadczeniem: 20-30 minut

---

## ✅ Checklist Pre-requisites

Przed rozpoczęciem upewnij się, że masz:

- [ ] Konto Azure z aktywną subskrypcją
- [ ] Azure CLI zainstalowane i zalogowane (`az login`)
- [ ] GitHub CLI zainstalowane (opcjonalne, ale polecane)
- [ ] Git zainstalowany
- [ ] Działająca aplikacja Streamlit lokalnie
- [ ] Plik `requirements.txt` z WSZYSTKIMI dependencies

**Test lokalny** (WAŻNE - zrób to przed wdrożeniem):
```bash
python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0
```
Jeśli nie działa lokalnie, nie będzie działać na Azure!

---

## 📝 Krok 1: Przygotowanie Projektu (5 min)

### 1.1 Struktura plików

Upewnij się, że masz tę minimalną strukturę:
```
twoj-projekt/
├── app.py                 # Główny plik Streamlit
├── requirements.txt       # Wszystkie dependencies
└── README.md             # Dokumentacja
```

### 1.2 Weryfikacja requirements.txt

**❌ CZĘSTY BŁĄD**: Brakujące lub niepełne dependencies

Wygeneruj pełną listę:
```bash
pip freeze > requirements.txt
```

Lub minimalna dla Streamlit:
```txt
streamlit>=1.40.1
pandas>=2.1.4
plotly>=5.18.0
numpy<2.0.0,>=1.26.3
```

**⚠️ WAŻNE**: Dodaj WSZYSTKIE biblioteki których używasz w kodzie!

### 1.3 Test lokalny

```bash
# Stwórz venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Zainstaluj dependencies
pip install -r requirements.txt

# Test aplikacji NA PORCIE 8000 (Azure requirement!)
python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0
```

Otwórz: http://localhost:8000

**Jeśli NIE działa** → Napraw najpierw lokalnie, potem deployment.

---

## 📝 Krok 2: Setup Azure Resources (10 min)

### 2.1 Zapisz zmienne (DOSTOSUJ DO SIEBIE)

```bash
# ZMIEŃ TE WARTOŚCI!
export PROJECT_NAME="moj-streamlit-app"
export RESOURCE_GROUP="${PROJECT_NAME}-rg"
export APP_SERVICE_PLAN="${PROJECT_NAME}-plan"
export WEB_APP_NAME="${PROJECT_NAME}-dashboard"  # Musi być globalnie unikalna!
export LOCATION="eastus"
```

**💡 TIP**: `WEB_APP_NAME` musi być unikalna w całym Azure. Dodaj cyfry/inicjały jeśli zajęta.

### 2.2 Utwórz Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

echo "✅ Resource Group utworzona: $RESOURCE_GROUP"
```

### 2.3 Utwórz App Service Plan

**❌ NIE UŻYWAJ**: Free tier (F1) - nie obsługuje Streamlit
**✅ UŻYWAJ**: Minimum B1 (Basic)

```bash
az appservice plan create \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

echo "✅ App Service Plan utworzony: $APP_SERVICE_PLAN (SKU: B1)"
```

**Koszt**: B1 ≈ $13/miesiąc

### 2.4 Utwórz Web App

```bash
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $WEB_APP_NAME \
  --runtime "PYTHON:3.11"

echo "✅ Web App utworzona: $WEB_APP_NAME"
echo "🌐 URL: https://${WEB_APP_NAME}.azurewebsites.net"
```

**Sprawdź czy nazwa została zaakceptowana** - jeśli błąd "already exists", zmień `WEB_APP_NAME`.

### 2.5 Skonfiguruj Startup Command

**🔥 KRYTYCZNE**: Streamlit wymaga specjalnej komendy startup!

```bash
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $WEB_APP_NAME \
  --startup-file "python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0"

echo "✅ Startup command skonfigurowany"
```

**Jeśli Twój główny plik ma inną nazwę** (np. `dashboard.py`):
```bash
--startup-file "python -m streamlit run dashboard.py --server.port=8000 --server.address=0.0.0.0"
```

### 2.6 Weryfikacja

```bash
# Sprawdź czy wszystko jest OK
az webapp show \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "{name:name, state:state, hostName:defaultHostName}" -o table

# Powinno pokazać:
# name                    state    hostName
# ----------------------  -------  ----------------------------------------
# twoj-app                Running  twoj-app.azurewebsites.net
```

---

## 📝 Krok 3: Service Principal (NIE Publish Profile!) (5 min)

**❌ BŁĄD Z PROJEKTU**: Publish Profile nie działa dobrze z GitHub Actions
**✅ ROZWIĄZANIE**: Service Principal

### 3.1 Pobierz Subscription ID

```bash
export SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Subscription ID: $SUBSCRIPTION_ID"
```

### 3.2 Utwórz Service Principal

**⚠️ Te dane są WRAŻLIWE - nie commituj do Git!**

```bash
az ad sp create-for-rbac \
  --name "github-actions-${PROJECT_NAME}" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --json-auth > /tmp/azure_credentials.json

echo "✅ Service Principal utworzony"
cat /tmp/azure_credentials.json
```

**Skopiuj cały JSON** - będzie potrzebny w następnym kroku!

Powinien wyglądać tak:
```json
{
  "clientId": "xxx-xxx-xxx",
  "clientSecret": "xxx-xxx-xxx",
  "subscriptionId": "xxx-xxx-xxx",
  "tenantId": "xxx-xxx-xxx"
}
```

### 3.3 Zweryfikuj uprawnienia

```bash
# Pobierz clientId z JSON
export CLIENT_ID=$(cat /tmp/azure_credentials.json | grep clientId | cut -d'"' -f4)

# Sprawdź uprawnienia
az role assignment list \
  --assignee $CLIENT_ID \
  --query "[].{Role:roleDefinitionName, Scope:scope}" -o table

# Powinno pokazać:
# Role         Scope
# -----------  ------------------------------------------------
# Contributor  /subscriptions/.../resourceGroups/twoj-rg
```

---

## 📝 Krok 4: Setup GitHub Repository (5 min)

### 4.1 Inicjalizacja Git (jeśli jeszcze nie zrobione)

```bash
# W katalogu projektu
git init
git add .
git commit -m "Initial commit: Streamlit dashboard"
```

### 4.2 Utwórz GitHub Repository

**Przez GitHub CLI** (najszybsze):
```bash
gh repo create $PROJECT_NAME --public --source=. --remote=origin --push
```

**Lub przez Web UI**:
1. Idź na https://github.com/new
2. Utwórz repozytorium
3. Pushuj kod:
```bash
git remote add origin https://github.com/TWOJ_USERNAME/$PROJECT_NAME.git
git branch -M main
git push -u origin main
```

### 4.3 Dodaj GitHub Secret

**Metoda 1: GitHub CLI** (najłatwiejsze):
```bash
gh secret set AZURE_CREDENTIALS < /tmp/azure_credentials.json
echo "✅ Secret AZURE_CREDENTIALS dodany"
```

**Metoda 2: Web UI**:
1. Idź do: Settings → Secrets and variables → Actions
2. Kliknij "New repository secret"
3. Name: `AZURE_CREDENTIALS`
4. Value: Wklej cały JSON z Service Principal
5. Kliknij "Add secret"

### 4.4 Weryfikacja

```bash
gh secret list
# Powinno pokazać:
# AZURE_CREDENTIALS  Updated 2025-11-09
```

### 4.5 Bezpieczeństwo

```bash
# Usuń lokalny plik z credentials!
rm /tmp/azure_credentials.json
echo "✅ Plik z credentials usunięty"
```

---

## 📝 Krok 5: Utworzenie Workflow File (5 min)

### 5.1 Utwórz strukturę

```bash
mkdir -p .github/workflows
```

### 5.2 Utwórz plik workflow

```bash
cat > .github/workflows/azure-deploy.yml << 'WORKFLOW_EOF'
name: Deploy to Azure App Service

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AZURE_WEBAPP_NAME: ZMIEN_MNIE          # ← ZMIEŃ NA SWOJĄ NAZWĘ!
  AZURE_RESOURCE_GROUP: ZMIEN_MNIE_RG   # ← ZMIEŃ NA SWOJĄ RESOURCE GROUP!
  PYTHON_VERSION: '3.11'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Login to Azure
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Create deployment package
      run: |
        # Spakuj aplikację do ZIP
        zip -r deploy.zip app.py requirements.txt

    - name: Deploy to Azure Web App
      run: |
        # Użyj async deployment aby uniknąć timeoutów
        az webapp deploy \
          --resource-group ${{ env.AZURE_RESOURCE_GROUP }} \
          --name ${{ env.AZURE_WEBAPP_NAME }} \
          --src-path deploy.zip \
          --type zip \
          --async true

        echo "✅ Deployment initiated successfully!"
        echo "🌐 App URL: https://${{ env.AZURE_WEBAPP_NAME }}.azurewebsites.net"

    - name: Logout from Azure
      run: az logout
      if: always()
WORKFLOW_EOF

echo "✅ Workflow file utworzony"
```

### 5.3 WAŻNE: Edytuj workflow file

**Otwórz** `.github/workflows/azure-deploy.yml` i **ZMIEŃ**:

```yaml
env:
  AZURE_WEBAPP_NAME: twoja-nazwa-app        # ← Z kroku 2
  AZURE_RESOURCE_GROUP: twoja-resource-group # ← Z kroku 2
  PYTHON_VERSION: '3.11'                     # ← Twoja wersja Python
```

**Podstaw wartości z kroku 2.1!**

### 5.4 Jeśli masz dodatkowe pliki

Jeśli Twoja aplikacja używa dodatkowych katalogów (np. `data/`, `config/`, `utils/`):

```yaml
- name: Create deployment package
  run: |
    # Dodaj wszystkie potrzebne pliki/katalogi
    zip -r deploy.zip app.py requirements.txt data/ config/ utils/
```

**Lub pakuj wszystko oprócz niepotrzebnych**:
```yaml
- name: Create deployment package
  run: |
    # Wyklucz .git, __pycache__, etc
    zip -r deploy.zip . \
      -x "*.git*" \
      -x "*__pycache__*" \
      -x "*.pyc" \
      -x "venv/*" \
      -x ".env*"
```

---

## 📝 Krok 6: Pierwszy Deployment (10 min)

### 6.1 Commit i Push

```bash
# Dodaj workflow
git add .github/workflows/azure-deploy.yml
git commit -m "Add Azure deployment workflow"
git push origin main

echo "✅ Workflow wypushowany - deployment powinien się rozpocząć automatycznie"
```

### 6.2 Monitorowanie (w przeglądarce)

1. Idź na GitHub → Zakładka **Actions**
2. Powinien się pokazać workflow "Deploy to Azure App Service"
3. Kliknij na niego i obserwuj logi

**Lub przez CLI**:
```bash
# Lista uruchomionych workflows
gh run list --limit 5

# Obserwuj live
gh run watch
```

### 6.3 Oczekiwany czas

- **Build & Package**: ~10-20 sekund
- **Deployment initiation**: ~10-30 sekund
- **Azure processing (w tle)**: ~5-8 minut

**⚠️ WAŻNE**: Workflow może zakończyć się po 30-60 sekundach dzięki `--async true`.
To jest **NORMALNE** - deployment kontynuuje się w tle na Azure.

### 6.4 Sprawdzenie czy deployment się powiódł

**Nie polegaj tylko na GitHub Actions!** Sprawdź Azure:

```bash
# Poczekaj 2-3 minuty po zakończeniu workflow, potem:

# Sprawdź status aplikacji
az webapp show \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "state" -o tsv
# Powinno zwrócić: Running

# Test HTTP
curl -I https://${WEB_APP_NAME}.azurewebsites.net
# Powinno zwrócić: HTTP/2 200
```

### 6.5 Pierwszy dostęp do aplikacji

Otwórz przeglądarkę:
```
https://TWOJA-NAZWA-APP.azurewebsites.net
```

**Pierwsze uruchomienie może trwać 1-2 minuty** - Azure instaluje dependencies.

---

## 🔍 Krok 7: Weryfikacja i Testy (5 min)

### 7.1 Checklist Weryfikacji

- [ ] Aplikacja otwiera się w przeglądarce
- [ ] Wszystkie strony/funkcje działają
- [ ] Nie ma błędów 500/503
- [ ] Dane wyświetlają się poprawnie
- [ ] Interaktywne elementy działają

### 7.2 Sprawdzenie logów (jeśli coś nie działa)

```bash
# Logi na żywo
az webapp log tail \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP

# Przerwij: Ctrl+C
```

**Typowe błędy w logach**:
- `ModuleNotFoundError` → Brak biblioteki w requirements.txt
- `Port 8501` → Zła startup command (musi być 8000!)
- `Application timeout` → Aplikacja za wolna, rozważ większy SKU

### 7.3 Test automatycznego deploymentu

Zrób małą zmianę w `app.py`:
```bash
# Np. dodaj komentarz
echo "# Test deployment" >> app.py

git add app.py
git commit -m "Test: automatic deployment"
git push origin main
```

Sprawdź czy workflow się uruchomił i deployment przeszedł.

---

## 🚨 Troubleshooting - Typowe Problemy

### Problem 1: "Application Error" po deploymencie

**Objawy**: Strona pokazuje "Application Error" lub HTTP 503

**Rozwiązanie**:

1. **Sprawdź logi**:
```bash
az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

2. **Najczęstsza przyczyna**: Zła startup command
```bash
# Sprawdź obecną
az webapp config show \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "appCommandLine"

# Ustaw poprawną
az webapp config set \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0"

# Restart
az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP
```

3. **Druga przyczyna**: Brak dependencies w requirements.txt
```bash
# Dodaj wszystkie używane biblioteki do requirements.txt
# Commitnij i pushuj - nowy deployment się uruchomi
```

### Problem 2: "504 Gateway Timeout" w GitHub Actions

**Objawy**: Workflow kończy się błędem 504 ale aplikacja działa

**✅ To jest OK!** - Właśnie dlatego używamy `--async true`

**Sprawdź czy deployment się powiódł**:
```bash
curl -I https://${WEB_APP_NAME}.azurewebsites.net
# Jeśli HTTP 200 - wszystko OK, ignore timeout w workflow
```

### Problem 3: "Invalid credentials" w workflow

**Objawy**: Workflow kończy się na kroku "Login to Azure"

**Rozwiązanie**:

1. Sprawdź czy secret istnieje:
```bash
gh secret list
```

2. Jeśli nie ma lub jest stary, utwórz nowy Service Principal:
```bash
# Usuń stary
az ad sp delete --id $(az ad sp list --display-name "github-actions-${PROJECT_NAME}" --query "[0].appId" -o tsv)

# Utwórz nowy (powtórz krok 3)
```

### Problem 4: "Resource not found"

**Objawy**: Workflow nie może znaleźć Web App lub Resource Group

**Rozwiązanie**: Sprawdź czy nazwy w workflow są DOKŁADNIE takie same jak w Azure:

```bash
# Sprawdź nazwy
echo "Resource Group: $RESOURCE_GROUP"
echo "Web App: $WEB_APP_NAME"

# Porównaj z workflow
cat .github/workflows/azure-deploy.yml | grep -A 2 "env:"
```

### Problem 5: Aplikacja działa lokalnie ale nie na Azure

**Przyczyny i rozwiązania**:

1. **Port** - Azure wymaga 8000, nie 8501
   - Sprawdź startup command (krok 2.5)

2. **Dependencies** - Brak bibliotek
   - `pip freeze > requirements.txt` i redeploy

3. **Ścieżki do plików** - Używasz absolute paths
   - Używaj relative paths: `./data/file.csv` nie `/Users/ja/projekt/data/file.csv`

4. **Zmienne środowiskowe** - Aplikacja potrzebuje ENV vars
   ```bash
   az webapp config appsettings set \
     --name $WEB_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --settings KEY1=value1 KEY2=value2
   ```

---

## 📊 Maintenance & Best Practices

### Monitoring

**Setup Application Insights** (opcjonalne ale polecane):
```bash
# Utwórz App Insights
az monitor app-insights component create \
  --app ${PROJECT_NAME}-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Połącz z Web App
az webapp config appsettings set \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show --app ${PROJECT_NAME}-insights --resource-group $RESOURCE_GROUP --query connectionString -o tsv)
```

### Scaling

**Manual scaling** (zwiększ liczbę instancji):
```bash
az appservice plan update \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --number-of-workers 2
```

**Auto-scaling** (produkcja):
```bash
# Wymaga minimum S1 tier
az appservice plan update \
  --name $APP_SERVICE_PLAN \
  --resource-group $RESOURCE_GROUP \
  --sku S1

az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource $APP_SERVICE_PLAN \
  --resource-type Microsoft.Web/serverfarms \
  --name ${PROJECT_NAME}-autoscale \
  --min-count 1 \
  --max-count 3 \
  --count 1
```

### Backup & Rollback

**Jeśli deployment się zepsuł**, wróć do poprzedniej wersji:

```bash
# Lista deploymentów
az webapp deployment list \
  --name $WEB_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "[].{id:id, status:status, author:author, start:startTime}" -o table

# Rollback przez GitHub
git revert HEAD
git push origin main
# Nowy deployment się uruchomi automatycznie
```

### Koszty

**Szacunkowe koszty miesięczne**:

| SKU  | vCPU | RAM    | Koszt/miesiąc | Zastosowanie          |
|------|------|--------|---------------|-----------------------|
| B1   | 1    | 1.75GB | ~$13          | Dev/Test/Small apps   |
| B2   | 2    | 3.5GB  | ~$26          | Medium traffic        |
| S1   | 1    | 1.75GB | ~$70          | Production + scaling  |
| P1v2 | 1    | 3.5GB  | ~$80          | Production + features |

**Sprawdź aktualne koszty**:
```bash
az consumption usage list \
  --start-date $(date -d "1 month ago" +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?contains(instanceName, '${WEB_APP_NAME}')]" -o table
```

---

## 🎓 Najważniejsze Zasady (Lekcje z Projektu)

### ✅ DO (Rób)

1. **Zawsze testuj lokalnie najpierw** - na porcie 8000!
2. **Używaj Service Principal** - nie publish profile
3. **Używaj async deployment** - unikniesz timeoutów
4. **Pełny requirements.txt** - `pip freeze > requirements.txt`
5. **Sprawdzaj logi Azure** - nie tylko GitHub Actions
6. **Commituj małe zmiany** - łatwiej debugować
7. **Backup przed dużymi zmianami** - git tag lub branch

### ❌ DON'T (Nie rób)

1. **Nie używaj Free tier (F1)** - nie obsługuje Streamlit
2. **Nie używaj publish profile** - problemy z GitHub Actions
3. **Nie używaj synchronicznego deployment** - timeouty
4. **Nie commituj credentials** - używaj secrets
5. **Nie zakładaj że workflow success = app działa** - sprawdź Azure!
6. **Nie wdrażaj bez testu lokalnego** - strata czasu
7. **Nie używaj absolute paths** - nie zadziała na Azure

---

## 🚀 Quick Commands Reference

### Codzienne użycie

```bash
# Status aplikacji
az webapp show --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP --query "state" -o tsv

# Restart aplikacji
az webapp restart --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Logi live
az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Test HTTP
curl -I https://${WEB_APP_NAME}.azurewebsites.net

# Lista deploymentów
gh run list --limit 10

# Trigger manual deployment
gh workflow run "Deploy to Azure App Service"
```

### Debugging

```bash
# Wszystkie konfiguracje
az webapp config show --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP

# Environment variables
az webapp config appsettings list --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP -o table

# Connection strings (jeśli używasz DB)
az webapp config connection-string list --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP -o table

# Deployment history
az webapp deployment list --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP -o table
```

---

## 📞 Gdzie Szukać Pomocy

### Dokumentacja
- [Azure App Service + Python](https://docs.microsoft.com/azure/app-service/quickstart-python)
- [Streamlit Deployment](https://docs.streamlit.io/knowledge-base/tutorials/deploy)
- [GitHub Actions - Azure](https://github.com/Azure/actions)

### Debugging Workflow
1. GitHub Actions → Kliknij na failed job → Zobacz szczegółowe logi
2. Azure Portal → App Service → Log Stream
3. Azure Portal → App Service → Deployment Center → Zobacz deployment logs

### Typowe Error Messages i Rozwiązania

| Error | Przyczyna | Rozwiązanie |
|-------|-----------|-------------|
| `ModuleNotFoundError: No module named 'streamlit'` | Brak w requirements.txt | Dodaj do requirements.txt i redeploy |
| `Application timeout` | Aplikacja za długo startuje | Zwiększ SKU lub zoptymalizuj kod |
| `Port 8501 is already in use` | Zła startup command | Ustaw port 8000 w startup command |
| `Invalid credentials` | Złe lub wygasłe credentials | Utwórz nowy Service Principal |
| `504 Gateway Timeout` | Sync deployment zbyt długi | Zmień na `--async true` (już jest!) |

---

## ✅ Deployment Checklist - Wydrukuj i Zaznaczaj!

```
PRE-DEPLOYMENT:
□ Aplikacja działa lokalnie na porcie 8000
□ requirements.txt jest kompletny
□ Kod jest w Git repository
□ Zmienne PROJECT_NAME, RESOURCE_GROUP, WEB_APP_NAME są ustawione

AZURE SETUP:
□ Resource Group utworzona
□ App Service Plan utworzony (minimum B1)
□ Web App utworzona z Python 3.11
□ Startup command skonfigurowany (port 8000!)
□ Service Principal utworzony
□ Uprawnienia Contributor zweryfikowane

GITHUB SETUP:
□ Repository utworzone
□ Secret AZURE_CREDENTIALS dodany
□ Workflow file utworzony w .github/workflows/
□ Nazwy w workflow odpowiadają Azure resources
□ Kod wypushowany do main

POST-DEPLOYMENT:
□ GitHub Actions workflow zakończony (może być success mimo timeout)
□ Azure Web App w stanie "Running"
□ HTTP test zwraca 200
□ Aplikacja otwiera się w przeglądarce
□ Wszystkie funkcje działają poprawnie
□ Logi nie pokazują błędów
□ Test automatycznego deploymentu (mała zmiana + push)

CLEANUP LOKALNY:
□ Plik azure_credentials.json usunięty
□ .env dodany do .gitignore (jeśli używasz)
□ Dokumentacja zaktualizowana
```

---

## 🎉 Gratulacje!

Jeśli przeszedłeś przez wszystkie kroki - masz w pełni funkcjonalny CI/CD pipeline dla Streamlit na Azure!

**Co dalej?**
- Dodaj custom domain
- Setup monitoring (Application Insights)
- Implementuj auto-scaling
- Dodaj testy automatyczne do workflow
- Setup staging environment

---

*Przewodnik oparty na: Rzeczywisty projekt azure-streamlit deployment*
*Ostatnia aktualizacja: 2025-11-09*
*Autor: Claude Code*
