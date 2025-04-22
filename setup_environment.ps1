# setup_environment.ps1
# Скрипт для настройки виртуального окружения и установки зависимостей

# Параметры скрипта
param (
    [switch]$Force = $false,  # Принудительное пересоздание окружения
    [string]$EnvName = "venv",  # Имя виртуального окружения
    [string[]]$RunTests = @(),  # Список тестов для запуска (пустой массив - без тестов)
    [switch]$RunAllTests = $false  # Запустить все доступные тесты
)

# Функция для вывода сообщений в цвете
function Write-ColorOutput {
    param (
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Функция для проверки наличия Python
function Check-Python {
    try {
        $pythonVersion = python --version
        Write-ColorOutput "✓ Python установлен: $pythonVersion" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "✗ Python не найден. Пожалуйста, установите Python 3.8 или выше." "Red"
        return $false
    }
}

# Функция для создания виртуального окружения
function Create-VirtualEnv {
    param (
        [string]$EnvName
    )
    
    if ((Test-Path $EnvName) -and -not $Force) {
        Write-ColorOutput "✓ Виртуальное окружение '$EnvName' уже существует." "Green"
        return $true
    }
    
    if ((Test-Path $EnvName) -and $Force) {
        Write-ColorOutput "♺ Удаление существующего виртуального окружения '$EnvName'..." "Yellow"
        Remove-Item -Recurse -Force $EnvName
    }
    
    Write-ColorOutput "⚙ Создание виртуального окружения '$EnvName'..." "Cyan"
    try {
        python -m venv $EnvName
        Write-ColorOutput "✓ Виртуальное окружение создано успешно!" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "✗ Ошибка при создании виртуального окружения: $_" "Red"
        return $false
    }
}

# Функция для активации виртуального окружения
function Activate-VirtualEnv {
    param (
        [string]$EnvName
    )
    
    $activateScript = Join-Path $EnvName "Scripts\Activate.ps1"
    
    if (-not (Test-Path $activateScript)) {
        Write-ColorOutput "✗ Файл активации виртуального окружения не найден: $activateScript" "Red"
        return $false
    }
    
    try {
        Write-ColorOutput "⚙ Активация виртуального окружения..." "Cyan"
        . $activateScript
        Write-ColorOutput "✓ Виртуальное окружение активировано!" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "✗ Ошибка при активации виртуального окружения: $_" "Red"
        return $false
    }
}

# Функция для установки зависимостей
function Install-Dependencies {
    if (-not (Test-Path "requirements.txt")) {
        Write-ColorOutput "✗ Файл requirements.txt не найден." "Red"
        return $false
    }
    
    Write-ColorOutput "⚙ Обновление pip..." "Cyan"
    python -m pip install --upgrade pip
    
    Write-ColorOutput "⚙ Установка зависимостей из requirements.txt..." "Cyan"
    try {
        python -m pip install -r requirements.txt
        Write-ColorOutput "✓ Зависимости установлены успешно!" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "✗ Ошибка при установке зависимостей: $_" "Red"
        return $false
    }
}

# Функция для создания структуры каталогов
function Create-Directories {
    $directories = @("inputs", "outputs", "outputs/images", "outputs/audio")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            Write-ColorOutput "⚙ Создание директории '$dir'..." "Cyan"
            mkdir $dir | Out-Null
        }
    }
    
    Write-ColorOutput "✓ Структура каталогов создана/проверена!" "Green"
    return $true
}

# Функция для получения списка всех доступных тестов
function Get-AvailableTests {
    $testFiles = Get-ChildItem -Path "tests" -Filter "test_*.py" -File
    return $testFiles | ForEach-Object { $_.Name }
}

# Функция для запуска конкретного теста
function Run-SingleTest {
    param (
        [string]$TestFile
    )
    
    # Проверяем, содержит ли путь директорию tests
    if ($TestFile -notmatch "tests[/\\]") {
        $TestFile = "tests/$TestFile"
    }
    
    if (-not (Test-Path $TestFile)) {
        Write-ColorOutput "✗ Тест '$TestFile' не найден." "Red"
        return $false
    }
    
    Write-ColorOutput "⚙ Запуск теста '$TestFile'..." "Cyan"
    python $TestFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✓ Тест '$TestFile' прошел успешно!" "Green"
        return $true
    } else {
        Write-ColorOutput "✗ Тест '$TestFile' не прошел. Проверьте вывод выше для получения дополнительной информации." "Red"
        return $false
    }
}

# Функция для запуска тестов
function Run-Tests {
    param (
        [string[]]$TestList = @(),
        [switch]$RunAll = $false
    )
    
    $allTests = Get-AvailableTests
    
    if ($allTests.Count -eq 0) {
        Write-ColorOutput "! Не найдено ни одного тестового файла (test_*.py)." "Yellow"
        return $true
    }
    
    if ($RunAll) {
        Write-ColorOutput "⚙ Запуск всех доступных тестов..." "Cyan"
        $TestList = $allTests
    }
    
    if ($TestList.Count -eq 0) {
        return $true
    }
    
    $allPassed = $true
    
    foreach ($test in $TestList) {
        # Если это просто имя теста без расширения, добавляем .py
        if ($test -notmatch "\.py$") {
            $test = "$test.py"
        }
        
        # Если это имя теста без полного пути, добавляем test_ префикс, если его нет
        if (($test -notmatch "^test_") -and ($test -notmatch "\\")) {
            $test = "test_$test"
        }
        
        # Если тест уже существует, запускаем его
        if (Test-Path $test) {
            $testPassed = Run-SingleTest -TestFile $test
        }
        # Пробуем с префиксом test_
        elseif (Test-Path "test_$test") {
            $testPassed = Run-SingleTest -TestFile "test_$test"
        }
        else {
            Write-ColorOutput "✗ Тест '$test' не найден." "Red"
            $testPassed = $false
        }
        
        $allPassed = $allPassed -and $testPassed
    }
    
    return $allPassed
}

# Основной сценарий
$title = @"
╔════════════════════════════════════════════════════════════════╗
║                  ChatGPT Video - Настройка среды                ║
╚════════════════════════════════════════════════════════════════╝
"@

Write-Host $title

# Проверка наличия Python
if (-not (Check-Python)) {
    exit 1
}

# Создание виртуального окружения
if (-not (Create-VirtualEnv -EnvName $EnvName)) {
    exit 1
}

# Активация виртуального окружения
if (-not (Activate-VirtualEnv -EnvName $EnvName)) {
    exit 1
}

# Установка зависимостей
if (-not (Install-Dependencies)) {
    exit 1
}

# Создание структуры каталогов
if (-not (Create-Directories)) {
    exit 1
}

# Запуск тестов
Write-Host ""
$availableTests = Get-AvailableTests
$testsToRun = $RunTests

# Если не указаны тесты для запуска, но выбран запуск всех тестов
if (($testsToRun.Count -eq 0) -and $RunAllTests) {
    Write-ColorOutput "⚙ Запуск всех доступных тестов..." "Cyan"
    Run-Tests -RunAll
}
# Если указаны конкретные тесты для запуска
elseif ($testsToRun.Count -gt 0) {
    Write-ColorOutput "⚙ Запуск указанных тестов: $($testsToRun -join ', ')..." "Cyan"
    Run-Tests -TestList $testsToRun
}
# Если не указаны тесты и не выбран запуск всех, предлагаем выбор
elseif ($availableTests.Count -gt 0) {
    Write-ColorOutput "Доступные тесты:" "Yellow"
    $i = 1
    foreach ($test in $availableTests) {
        Write-ColorOutput "  $i. $test" "Yellow"
        $i++
    }
    Write-ColorOutput "  A. Запустить все тесты" "Yellow"
    Write-ColorOutput "  N. Не запускать тесты" "Yellow"
    
    $choice = Read-Host "Выберите тесты для запуска (номера через запятую, A для всех, N для пропуска)"
    
    if ($choice -eq "A") {
        Run-Tests -RunAll
    }
    elseif ($choice -ne "N") {
        $selectedIndices = $choice -split ',' | ForEach-Object { $_.Trim() }
        $selectedTests = @()
        
        foreach ($index in $selectedIndices) {
            $i = [int]$index
            if ($i -gt 0 -and $i -le $availableTests.Count) {
                $selectedTests += $availableTests[$i-1]
            }
        }
        
        if ($selectedTests.Count -gt 0) {
            Run-Tests -TestList $selectedTests
        }
    }
}

Write-ColorOutput @"

╔════════════════════════════════════════════════════════════════╗
║                      Настройка завершена!                       ║
║                                                                 ║
║  Для запуска проекта:                                          ║
║  1. Активируйте окружение: . .\$EnvName\Scripts\Activate.ps1     ║
║  2. Запустите скрипт: python main.py                           ║
║                                                                 ║
║  Дополнительные параметры:                                     ║
║  - Выбор движка AI: python main.py --engine [ollama/llamacpp/yandexgpt] ║
║  - Параллельная обработка: python main.py --parallel           ║
║                                                                 ║
║  Для запуска тестов:                                           ║
║  - Все тесты: .\setup_environment.ps1 -RunAllTests             ║
║  - Конкретный тест: .\setup_environment.ps1 -RunTests pdf_extraction ║
╚════════════════════════════════════════════════════════════════╝
"@ "Cyan"
