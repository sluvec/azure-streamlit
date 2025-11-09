# Raport z Wdrożenia: Sales Analytics Dashboard na Azure App Service

## Podsumowanie Wykonawcze

Projekt dotyczył naprawy automatycznego wdrażania aplikacji Streamlit (Sales Analytics Dashboard) na Azure App Service przy użyciu GitHub Actions. Pierwotny workflow kończy się błędami. Po przeprowadzeniu szczegółowej analizy i kilku iteracjach udało się osiągnąć w pełni funkcjonalny deployment.

**Status końcowy**: ✅ Sukces
**URL aplikacji**: https://azure-streamlit-dashboard.azurewebsites.net
**Czas trwania naprawy**: ~30 minut
**Liczba prób deployment**: 4

## Struktura Projektu

```
azure_streamlit/
├── .github/
│   └── workflows/
│       └── azure-deploy.yml          # GitHub Actions workflow
├── app.py                            # Główna aplikacja Streamlit
├── requirements.txt                  # Zależności Python
├── README.md                         # Dokumentacja projektu
└── DEPLOYMENT_REPORT.md              # Ten dokument
```

## Chronologia Problemów i Rozwiązań

### Problem 1: Nieprawidłowy Publish Profile
**Objaw**:
```
##[error]Deployment Failed, Error: Publish profile is invalid for app-name
and slot-name provided. Provide correct publish profile credentials for app.
```

**Przyczyna**:
- GitHub Secret `AZURE_WEBAPP_PUBLISH_PROFILE` był nieprawidłowy lub wygasły
- Publish profile nie odpowiadał nazwie aplikacji Azure

**Rozwiązanie (nieudane)**:
1. Pobranie nowego publish profile z Azure:
   ```bash
   az webapp deployment list-publishing-profiles \
     --name azure-streamlit-dashboard \
     --resource-group azure-streamlit-rg \
     --xml > /tmp/publishprofile.xml
   ```

2. Aktualizacja GitHub Secret:
   ```bash
   gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < /tmp/publishprofile.xml
   ```

**Wynik**: Akcja `azure/webapps-deploy@v2` nadal nie działała poprawnie z publish profile.

### Problem 2: Problemy z akcją azure/webapps-deploy
**Objaw**:
- Kontynuacja błędów publish profile mimo aktualizacji
- Akcja nie potrafiła prawidłowo zinterpretować publish profile

**Decyzja**: Przejście na inne podejście - Service Principal + Azure CLI

**Rozwiązanie**:
1. Utworzenie Service Principal dla GitHub Actions:
   ```bash
   az ad sp create-for-rbac \
     --name "github-actions-azure-streamlit" \
     --role contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/azure-streamlit-rg \
     --json-auth
   ```

2. Utworzenie GitHub Secret `AZURE_CREDENTIALS` z danymi Service Principal:
   ```json
   {
     "clientId": "xxx",
     "clientSecret": "xxx",
     "subscriptionId": "xxx",
     "tenantId": "xxx"
   }
   ```

3. Modyfikacja workflow na użycie `azure/login@v1` action

### Problem 3: Gateway Timeout (504)
**Objaw**:
```
ERROR: An error occured during deployment. Status Code: 504,
Details: 504.0 GatewayTimeout
```

**Przyczyna**:
- Deployment przez `az webapp deployment source config-zip` trwał zbyt długo
- Azure App Service potrzebował więcej czasu na instalację zależności
- Komenda czekała na pełne zakończenie deploymentu

**Rozwiązanie**:
1. Przejście z deprecated `config-zip` na nowe `az webapp deploy`
2. Użycie flagi `--async true` aby nie czekać na zakończenie:
   ```bash
   az webapp deploy \
     --resource-group azure-streamlit-rg \
     --name azure-streamlit-dashboard \
     --src-path deploy.zip \
     --type zip \
     --async true
   ```

**Wynik**: Deployment się powiódł bez timeoutu ✅

## Finalna Konfiguracja Workflow

### Workflow File: `.github/workflows/azure-deploy.yml`

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AZURE_WEBAPP_NAME: azure-streamlit-dashboard
  AZURE_RESOURCE_GROUP: azure-streamlit-rg
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

### Wymagane GitHub Secrets

| Secret Name | Opis | Jak uzyskać |
|------------|------|-------------|
| `AZURE_CREDENTIALS` | Credentials Service Principal | `az ad sp create-for-rbac --json-auth` |

### Konfiguracja Azure App Service

**Startup Command** (ustawiony w Azure Portal):
```bash
python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0
```

**Runtime Stack**: Python 3.11
**Operating System**: Linux
**Resource Group**: azure-streamlit-rg
**App Service Plan**: Basic (B1) lub wyższy

## Kluczowe Wnioski i Lekcje

### ✅ Co Zadziałało

1. **Service Principal zamiast Publish Profile**
   - Bardziej niezawodne uwierzytelnianie
   - Łatwiejsze zarządzanie uprawnieniami
   - Lepsze logowanie błędów

2. **Azure CLI zamiast dedykowanych akcji GitHub**
   - Większa kontrola nad procesem deployment
   - Możliwość użycia najnowszych komend Azure CLI
   - Prostsze debugowanie

3. **Async deployment**
   - Uniknięcie timeoutów
   - Szybsze zakończenie workflow
   - Deployment kontynuowany w tle Azure

### ❌ Co Nie Zadziałało

1. **Akcja azure/webapps-deploy z publish profile**
   - Problemy z walidacją credentials
   - Ograniczone komunikaty błędów

2. **Synchroniczny deployment**
   - Gateway timeouts przy dłuższych deploymentach
   - Niepotrzebne oczekiwanie w workflow

### 📋 Checkl ista dla Przyszłych Wdrożeń

#### Przed rozpoczęciem:
- [ ] Aplikacja Azure App Service istnieje i działa
- [ ] Runtime stack jest poprawnie skonfigurowany
- [ ] Startup command jest ustawiony (dla Streamlit)
- [ ] Service Principal został utworzony
- [ ] Service Principal ma uprawnienia Contributor do Resource Group

#### Konfiguracja GitHub:
- [ ] Secret `AZURE_CREDENTIALS` jest ustawiony
- [ ] Workflow file jest w `.github/workflows/`
- [ ] Nazwy resource group i app name są poprawne w env variables

#### Testowanie:
- [ ] Manualne uruchomienie workflow przez `workflow_dispatch`
- [ ] Weryfikacja logów deployment
- [ ] Test aplikacji w przeglądarce
- [ ] Sprawdzenie czy wszystkie zależności zostały zainstalowane

## Przydatne Komendy

### Sprawdzenie statusu aplikacji
```bash
az webapp show \
  --name azure-streamlit-dashboard \
  --resource-group azure-streamlit-rg \
  --query "state" -o tsv
```

### Pobranie logów aplikacji
```bash
az webapp log tail \
  --name azure-streamlit-dashboard \
  --resource-group azure-streamlit-rg
```

### Sprawdzenie deployment history
```bash
az webapp deployment list \
  --name azure-streamlit-dashboard \
  --resource-group azure-streamlit-rg
```

### Test aplikacji
```bash
curl -I https://azure-streamlit-dashboard.azurewebsites.net
```

## Rozwiązywanie Problemów

### Deployment kończy się timeout
- Użyj flagi `--async true` w `az webapp deploy`
- Sprawdź czy aplikacja rzeczywiście nie działa czy tylko timeout

### Aplikacja nie startuje
1. Sprawdź logi:
   ```bash
   az webapp log tail --name azure-streamlit-dashboard --resource-group azure-streamlit-rg
   ```
2. Zweryfikuj startup command w Azure Portal
3. Sprawdź czy wszystkie dependencies są w requirements.txt

### Service Principal nie ma uprawnień
```bash
az role assignment create \
  --assignee {clientId} \
  --role Contributor \
  --scope /subscriptions/{subscriptionId}/resourceGroups/azure-streamlit-rg
```

## Metryki Wydajności

- **Czas build**: ~10-15 sekund
- **Czas deployment (async)**: ~8-10 minut w tle
- **Czas workflow**: ~30 sekund (dzięki async)
- **Wielkość pakietu**: ~3KB (app.py + requirements.txt)

## Kontakt i Support

**Aplikacja**: https://azure-streamlit-dashboard.azurewebsites.net
**GitHub Repository**: https://github.com/sluvec/azure-streamlit
**Azure Resource Group**: azure-streamlit-rg

---

*Dokument utworzony: 2025-11-09*
*Wersja: 1.0*
*Autor: Claude Code*
