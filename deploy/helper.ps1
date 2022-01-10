function Load-DotEnv() {
    $content = Get-Content ".env" -ErrorAction Stop

    #load the content to environment
    foreach ($Line in $content) {
        if ($Line.StartsWith("#")) { continue };
        if ($Line.Trim()) {
            $Line = $Line.Replace("`"","")
            $KVP = $Line -split "=",2
            $Key = $KVP[0]
            $Value = $KVP[1]
            Set-Item -Path Env:$Key -Value $Value
        }
    }
}

function Get-My-IPAddress() {
    param ([string] $Network)
    return (Get-NetIPAddress |
        Where-Object {$_.AddressState -eq "Preferred" } |
        Where-Object {$_.IPAddress -like $Network} |
        Select-Object -Property IPAddress -First 1).IPAddress
}


$ContainerName = "pse-scrapping-service"
$ImageName = "pse-scrapping-service"
$ImageTag = "${ImageName}:latest"
$ImageFilePath = "./image.tar"


function Import-Image {
    Write-Output "Importing ${ImageName} from ${ImageFilePath}"
    docker rmi ${ImageTag}
    docker load -i ${ImageFilePath}
    Write-Output "Done"
}

function Stop-And-Remove {
    Write-Output "Stopping and removing ${ContainerName}"
    docker stop ${ContainerName}
    docker rm ${ContainerName}
    Write-Output "Done"
}

function Run-Image {
    Load-DotEnv
    $IPAddress = Get-My-IPAddress -Network ${Env:IP_ADDRESS_TEMPLATE}
    if (!$IPAddress) {
        $IPAddress = "0.0.0.0"
    }

    Write-Output "Running ${ImageTag} as ${Env:BIND_PORT} (${IPAddress}:${Env:CONTAINER_PORT})"
    docker run `
        --detach `
        --publish ${IPAddress}:${Env:CONTAINER_PORT}:${Env:BIND_PORT} `
        --mount type=volume,src=${ContainerName}-volume,dst=${Env:DATA_FOLDER}`
        --name ${ContainerName} `
        ${ImageTag}
    Write-Output "Done"
}

function Build-Image() {
    Load-DotEnv
   
    Write-Output "Building image ${ImageName}"
    docker build -f .\deploy\Dockerfile . `
        --build-arg PSE_USERNAME=${Env:PSE_USERNAME} `
        --build-arg PSE_PASSWORD=${Env:PSE_PASSWORD} `
        --build-arg CACHE_DURATION_HOURS=${Env:CACHE_DURATION_HOURS} `
        --build-arg DATA_FOLDER=${Env:DATA_FOLDER} `
        --build-arg BIND_IP_ADDRESS=${Env:BIND_IP_ADDRESS} `
        --build-arg BIND_PORT=${Env:BIND_PORT} `
        --tag ${ImageTag}
    Write-Output "Done"
}

function Export-Docker() {
    Write-Output "Saving image ${ImageTag} to ${ImageFilePath}"
    docker save -o ${ImageFilePath} ${ImageTag}
    Write-Output "Done"
}

$Command = $args[0]
if (!$Command) {
    throw "Provide argument - stop, run, build, export, import"
}

if ($Command -eq "stop") {
    Stop-And-Remove
}
if ($Command -eq "run") {
    Run-Image
}
if ($Command -eq "build") {
    Build-Image
}
if ($Command -eq "export") {
    Export-Docker
}
if ($Command -eq "import") {
    Import-Image
}
