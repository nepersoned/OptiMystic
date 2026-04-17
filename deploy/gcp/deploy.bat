@echo off
setlocal EnableDelayedExpansion

set PROJECT_ID=optimystic-493605
set REGION=asia-northeast3
set SERVICE_NAME=optimystic-api
set REPOSITORY=optimystic
set IMAGE_NAME=api
set IMAGE_TAG=latest
set ENV_FILE=deploy\gcp\.env.app

set IMAGE_URI=%REGION%-docker.pkg.dev/%PROJECT_ID%/%REPOSITORY%/%IMAGE_NAME%:%IMAGE_TAG%
set GCLOUD="C:\Users\kevin\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

echo ===============================================
echo  OptiMystic API to Google Cloud Run Deployment
echo ===============================================
echo.
echo  Project:   %PROJECT_ID%
echo  Region:    %REGION%
echo  Service:   %SERVICE_NAME%
echo  Image:     %IMAGE_URI%
echo.

echo [1/6] Setting project...
call %GCLOUD% config set project %PROJECT_ID%
if errorlevel 1 goto :error
echo Done.

echo.
echo [2/6] Enabling APIs...
call %GCLOUD% services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project=%PROJECT_ID%
if errorlevel 1 goto :error
echo Done.

echo.
echo [3/6] Ensuring Artifact Registry repo...
call %GCLOUD% artifacts repositories describe %REPOSITORY% --location=%REGION% --project=%PROJECT_ID% >nul 2>&1
if errorlevel 1 (
    echo Creating repository...
    call %GCLOUD% artifacts repositories create %REPOSITORY% --repository-format=docker --location=%REGION% --description="OptiMystic API images" --project=%PROJECT_ID%
    if errorlevel 1 goto :error
) else (
    echo Repository exists.
)

echo.
echo [4/6] Building container image ^(Cloud Build^)...
call %GCLOUD% builds submit --project=%PROJECT_ID% --tag %IMAGE_URI% --file docker/Dockerfile .
if errorlevel 1 goto :error

echo.
echo [5/6] Deploying to Cloud Run...

set ENV_VARS=
if exist %ENV_FILE% (
    for /f "usebackq eol=# tokens=*" %%a in ("%ENV_FILE%") do (
        if not "%%a"=="" (
            if defined ENV_VARS (
                set ENV_VARS=!ENV_VARS!,%%a
            ) else (
                set ENV_VARS=%%a
            )
        )
    )
)

if defined ENV_VARS (
    call %GCLOUD% run deploy %SERVICE_NAME% --image=%IMAGE_URI% --region=%REGION% --platform=managed --project=%PROJECT_ID% --port=8000 --memory=2Gi --cpu=2 --timeout=900 --concurrency=4 --no-allow-unauthenticated --set-env-vars="%ENV_VARS%"
) else (
    call %GCLOUD% run deploy %SERVICE_NAME% --image=%IMAGE_URI% --region=%REGION% --platform=managed --project=%PROJECT_ID% --port=8000 --memory=2Gi --cpu=2 --timeout=900 --concurrency=4 --no-allow-unauthenticated
)
if errorlevel 1 goto :error

echo.
echo [6/6] Getting service URL...
for /f "usebackq" %%u in (`call %GCLOUD% run services describe %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID% --format="value(status.url)"`) do set SERVICE_URL=%%u

echo.
echo ===============================================
echo  Deployment Successful!
echo ===============================================
echo.
echo Service URL: %SERVICE_URL%
echo.
echo Test the API:
echo   curl %SERVICE_URL%/health
echo.
goto :end

:error
echo.
echo ERROR: Deployment failed at the above step.
exit /b 1

:end
endlocal
