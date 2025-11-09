# Szablon: Wdrażanie Aplikacji Streamlit na Azure przez GitHub Actions

Ten dokument zawiera kompletny szablon i instrukcje konfiguracji automatycznego wdrażania aplikacji Streamlit na Azure App Service przy użyciu GitHub Actions.

## Spis Treści
1. [Wymagania Wstępne](#wymagania-wstępne)
2. [Krok 1: Konfiguracja Azure App Service](#krok-1-konfiguracja-azure-app-service)
3. [Krok 2: Utworzenie Service Principal](#krok-2-utworzenie-service-principal)
4. [Krok 3: Konfiguracja GitHub Secrets](#krok-3-konfiguracja-github-secrets)
5. [Krok 4: Utworzenie Workflow File](#krok-4-utworzenie-workflow-file)
6. [Krok 5: Testowanie i Weryfikacja](#krok-5-testowanie-i-weryfikacja)
7. [Troubleshooting](#troubleshooting)

---

## Wymagania Wstępne

### Narzędzia
- Azure CLI zainstalowane i skonfigurowane
- GitHub CLI (opcjonalnie, dla łatwiejszego zarządzania secrets)
- Git
- Konto Azure z aktywną subskrypcją
- Repozytorium GitHub

### Pliki wymagane w projekcie
```
projekt/
├── app.py                 # Główny plik aplikacji Streamlit
├── requirements.txt       # Zależności Python
└── .github/
    └── workflows/
        └── azure-deploy.yml  # Workflow file
```

### Przykładowy requirements.txt
```txt
streamlit>=1.40.1
pandas>=2.1.4
plotly>=5.18.0
numpy<2.0.0,>=1.26.3
```

---

## Krok 1: Konfiguracja Azure App Service

### 1.1 Utworzenie Resource Group

```bash
az group create \
  --name <RESOURCE_GROUP_NAME> \
  --location eastus
```

**Przykład**:
```bash
az group create \
  --name streamlit-app-rg \
  --location eastus
```

### 1.2 Utworzenie App Service Plan

```bash
az appservice plan create \
  --name <APP_SERVICE_PLAN_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --sku B1 \
  --is-linux
```

**Przykład**:
```bash
az appservice plan create \
  --name streamlit-plan \
  --resource-group streamlit-app-rg \
  --sku B1 \
  --is-linux
```

**Uwaga**: SKU B1 (Basic) to minimum dla aplikacji Streamlit. Dla produkcji rozważ S1 lub wyżej.

### 1.3 Utworzenie Web App

```bash
az webapp create \
  --resource-group <RESOURCE_GROUP_NAME> \
  --plan <APP_SERVICE_PLAN_NAME> \
  --name <WEB_APP_NAME> \
  --runtime "PYTHON:3.11"
```

**Przykład**:
```bash
az webapp create \
  --resource-group streamlit-app-rg \
  --plan streamlit-plan \
  --name my-streamlit-dashboard \
  --runtime "PYTHON:3.11"
```

**Ważne**: `<WEB_APP_NAME>` musi być globalnie unikalne w Azure.

### 1.4 Konfiguracja Startup Command

```bash
az webapp config set \
  --resource-group <RESOURCE_GROUP_NAME> \
  --name <WEB_APP_NAME> \
  --startup-file "python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0"
```

**Uwagi**:
- Port 8000 jest wymagany przez Azure App Service
- `--server.address=0.0.0.0` umożliwia dostęp zewnętrzny
- Dostosuj `app.py` do nazwy swojego głównego pliku

### 1.5 Weryfikacja konfiguracji

```bash
az webapp show \
  --name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --query "defaultHostName" -o tsv
```

Zapisz zwrócony URL - to będzie adres Twojej aplikacji.

---

## Krok 2: Utworzenie Service Principal

Service Principal to tożsamość używana przez GitHub Actions do uwierzytelniania w Azure.

### 2.1 Uzyskanie Subscription ID

```bash
az account show --query id -o tsv
```

Zapisz wynik - będzie potrzebny w następnym kroku.

### 2.2 Utworzenie Service Principal

```bash
az ad sp create-for-rbac \
  --name "github-actions-<PROJECT_NAME>" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP_NAME> \
  --json-auth
```

**Przykład**:
```bash
az ad sp create-for-rbac \
  --name "github-actions-streamlit-app" \
  --role contributor \
  --scopes /subscriptions/12345678-1234-1234-1234-123456789012/resourceGroups/streamlit-app-rg \
  --json-auth
```

**Wynik** (zapisz cały JSON):
```json
{
  "clientId": "xxx-xxx-xxx",
  "clientSecret": "xxx-xxx-xxx",
  "subscriptionId": "xxx-xxx-xxx",
  "tenantId": "xxx-xxx-xxx"
}
```

**⚠️ UWAGA**: To są wrażliwe dane! Nigdy nie commituj ich do repozytorium.

### 2.3 Weryfikacja uprawnień

```bash
az role assignment list \
  --assignee <CLIENT_ID> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

---

## Krok 3: Konfiguracja GitHub Secrets

### 3.1 Przez GitHub Web Interface

1. Przejdź do swojego repozytorium na GitHub
2. Kliknij **Settings** → **Secrets and variables** → **Actions**
3. Kliknij **New repository secret**
4. Nazwa: `AZURE_CREDENTIALS`
5. Wartość: Wklej cały JSON z kroku 2.2
6. Kliknij **Add secret**

### 3.2 Przez GitHub CLI

```bash
# Zapisz credentials do pliku tymczasowego
cat > /tmp/azure_credentials.json <<'EOF'
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx"
}
EOF

# Ustaw secret
gh secret set AZURE_CREDENTIALS < /tmp/azure_credentials.json

# Usuń plik tymczasowy
rm /tmp/azure_credentials.json
```

### 3.3 Weryfikacja

```bash
gh secret list
```

Powinieneś zobaczyć `AZURE_CREDENTIALS` na liście.

---

## Krok 4: Utworzenie Workflow File

### 4.1 Struktura katalogów

Utwórz strukturę katalogów:
```bash
mkdir -p .github/workflows
```

### 4.2 Szablon Workflow

Utwórz plik `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AZURE_WEBAPP_NAME: <YOUR_WEB_APP_NAME>
  AZURE_RESOURCE_GROUP: <YOUR_RESOURCE_GROUP_NAME>
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
        # Create zip file with all necessary files
        zip -r deploy.zip app.py requirements.txt

    - name: Deploy to Azure Web App
      run: |
        az webapp deploy \
          --resource-group ${{ env.AZURE_RESOURCE_GROUP }} \
          --name ${{ env.AZURE_WEBAPP_NAME }} \
          --src-path deploy.zip \
          --type zip \
          --async true

        echo "Deployment initiated successfully!"
        echo "App URL: https://${{ env.AZURE_WEBAPP_NAME }}.azurewebsites.net"

    - name: Logout from Azure
      run: az logout
      if: always()
```

### 4.3 Dostosowanie do Twojego Projektu

**Zmień**:
- `<YOUR_WEB_APP_NAME>` → nazwa Twojej aplikacji Azure
- `<YOUR_RESOURCE_GROUP_NAME>` → nazwa Twojej resource group
- `PYTHON_VERSION` → wersja Python (zgodna z Azure runtime)

**Jeśli masz dodatkowe pliki** (np. `data/`, `config/`):
```yaml
- name: Create deployment package
  run: |
    # Include additional files/directories
    zip -r deploy.zip app.py requirements.txt data/ config/
```

**Dla projektów z wieloma plikami Python**:
```yaml
- name: Create deployment package
  run: |
    # Exclude unnecessary files
    zip -r deploy.zip . -x "*.git*" -x "*__pycache__*" -x "*.pyc" -x "venv/*"
```

### 4.4 Commit i Push

```bash
git add .github/workflows/azure-deploy.yml
git commit -m "Add Azure deployment workflow"
git push origin main
```

---

## Krok 5: Testowanie i Weryfikacja

### 5.1 Manualne uruchomienie workflow

1. Przejdź do GitHub → **Actions**
2. Wybierz workflow **Deploy to Azure App Service**
3. Kliknij **Run workflow** → **Run workflow**

### 5.2 Monitorowanie deploymentu

**Przez GitHub**:
- Kliknij na uruchomiony workflow
- Obserwuj logi w czasie rzeczywistym

**Przez Azure CLI**:
```bash
# Status aplikacji
az webapp show \
  --name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --query "state" -o tsv

# Logi aplikacji
az webapp log tail \
  --name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME>
```

### 5.3 Weryfikacja aplikacji

```bash
# Test HTTP
curl -I https://<WEB_APP_NAME>.azurewebsites.net

# Powinien zwrócić HTTP/2 200
```

**W przeglądarce**:
Otwórz `https://<WEB_APP_NAME>.azurewebsites.net`

### 5.4 Sprawdzenie logów deployment

```bash
az webapp deployment list \
  --name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --query "[0].{id:id, status:status, author:author}" -o table
```

---

## Troubleshooting

### Problem: "Deployment Failed - Invalid credentials"

**Objawy**:
```
Error: Login failed
```

**Rozwiązanie**:
1. Sprawdź czy secret `AZURE_CREDENTIALS` jest poprawnie ustawiony
2. Zweryfikuj czy Service Principal ma uprawnienia:
   ```bash
   az role assignment list --assignee <CLIENT_ID>
   ```
3. Odtwórz Service Principal jeśli potrzeba

### Problem: "504 Gateway Timeout"

**Objawy**:
```
ERROR: Status Code: 504, Details: 504.0 GatewayTimeout
```

**Rozwiązanie**:
✅ To jest normalny błąd przy długich deploymentach!

1. Sprawdź czy deployment faktycznie nie powiódł się:
   ```bash
   curl -I https://<WEB_APP_NAME>.azurewebsites.net
   ```
2. Jeśli aplikacja działa (HTTP 200), ignore timeout
3. Upewnij się, że używasz flagi `--async true` w workflow

### Problem: "Application Error" po deployment

**Objawy**:
- Strona pokazuje "Application Error"
- HTTP 500 lub 503

**Rozwiązanie**:

1. **Sprawdź logi**:
   ```bash
   az webapp log tail \
     --name <WEB_APP_NAME> \
     --resource-group <RESOURCE_GROUP_NAME>
   ```

2. **Zweryfikuj startup command**:
   ```bash
   az webapp config show \
     --name <WEB_APP_NAME> \
     --resource-group <RESOURCE_GROUP_NAME> \
     --query "appCommandLine"
   ```

3. **Sprawdź czy requirements.txt jest kompletny**:
   - Wszystkie używane biblioteki są wymienione
   - Wersje są kompatybilne

4. **Test lokalny**:
   ```bash
   python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0
   ```

### Problem: "Deployment is taking too long"

**Objawy**:
- Workflow trwa > 5 minut
- Brak postępu w logach

**Rozwiązanie**:

1. **Sprawdź rozmiar dependencies**:
   ```bash
   pip list --format=freeze | wc -l
   ```
   Jeśli > 50 pakietów, rozważ:
   - Usunięcie nieużywanych dependencies
   - Użycie Docker image zamiast zip deploy

2. **Zwiększ App Service Plan**:
   ```bash
   az appservice plan update \
     --name <PLAN_NAME> \
     --resource-group <RESOURCE_GROUP_NAME> \
     --sku S1
   ```

### Problem: "Resource not found"

**Objawy**:
```
ERROR: Resource group 'xxx' could not be found
```

**Rozwiązanie**:

1. Sprawdź czy nazwa resource group w workflow jest poprawna
2. Zweryfikuj czy resource group istnieje:
   ```bash
   az group show --name <RESOURCE_GROUP_NAME>
   ```
3. Sprawdź czy Service Principal ma dostęp do resource group

---

## Dodatkowe Konfiguracje

### Zmienne środowiskowe w Azure

Jeśli aplikacja wymaga zmiennych środowiskowych:

```bash
az webapp config appsettings set \
  --name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --settings KEY1=value1 KEY2=value2
```

### Konfiguracja Custom Domain

```bash
# Dodaj custom domain
az webapp config hostname add \
  --webapp-name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --hostname www.twojadomena.pl

# Włącz HTTPS
az webapp config ssl bind \
  --name <WEB_APP_NAME> \
  --resource-group <RESOURCE_GROUP_NAME> \
  --certificate-thumbprint <THUMBPRINT> \
  --ssl-type SNI
```

### Scaling (Auto-scaling)

```bash
# Włącz auto-scaling
az monitor autoscale create \
  --resource-group <RESOURCE_GROUP_NAME> \
  --resource <APP_SERVICE_PLAN_ID> \
  --resource-type Microsoft.Web/serverfarms \
  --name autoscale-settings \
  --min-count 1 \
  --max-count 5 \
  --count 1
```

---

## Checklist Deployment

Przed pierwszym deploymentem:

### Azure Setup
- [ ] Resource Group utworzona
- [ ] App Service Plan utworzony (minimum B1)
- [ ] Web App utworzona z Python runtime
- [ ] Startup command skonfigurowany
- [ ] Service Principal utworzony z uprawnieniami Contributor

### GitHub Setup
- [ ] Repository utworzone
- [ ] Secret `AZURE_CREDENTIALS` ustawiony
- [ ] Workflow file dodany do `.github/workflows/`
- [ ] Nazwy resource group i app name są poprawne

### Kod
- [ ] `app.py` istnieje i działa lokalnie
- [ ] `requirements.txt` zawiera wszystkie dependencies
- [ ] Aplikacja testowana lokalnie na porcie 8000

### Testing
- [ ] Workflow uruchomiony manualnie i zakończony sukcesem
- [ ] Aplikacja dostępna pod Azure URL
- [ ] Wszystkie funkcje aplikacji działają poprawnie
- [ ] Logi nie pokazują błędów

---

## Wzorzec Deployment Flow

```
┌─────────────────┐
│  Git Push       │
│  to main        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Actions  │
│ triggered       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Checkout code   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Login to Azure  │
│ (Service        │
│  Principal)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create ZIP      │
│ package         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Deploy to Azure │
│ (async)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Azure processes │
│ deployment      │
│ in background   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ App running!    │
└─────────────────┘
```

---

## Przydatne Komendy - Quick Reference

```bash
# Sprawdź status aplikacji
az webapp show --name <NAME> --resource-group <RG> --query "state" -o tsv

# Logi na żywo
az webapp log tail --name <NAME> --resource-group <RG>

# Restart aplikacji
az webapp restart --name <NAME> --resource-group <RG>

# Lista deploymentów
az webapp deployment list --name <NAME> --resource-group <RG>

# Sprawdź konfigurację
az webapp config show --name <NAME> --resource-group <RG>

# Test HTTP
curl -I https://<NAME>.azurewebsites.net
```

---

## Koszt Estymacja

Przybliżone koszty miesięczne dla różnych planów:

| Plan | vCPU | RAM | Koszt/miesiąc | Zastosowanie |
|------|------|-----|---------------|--------------|
| B1   | 1    | 1.75GB | ~$13 | Development/Testing |
| S1   | 1    | 1.75GB | ~$70 | Small Production |
| P1v2 | 1    | 3.5GB  | ~$80 | Production |

**Uwaga**: Ceny mogą się różnić w zależności od regionu i promocji.

---

## Zasoby i Linki

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)

---

*Szablon utworzony: 2025-11-09*
*Wersja: 1.0*
*Bazuje na: Projekt azure-streamlit deployment*
*Autor: Claude Code*
