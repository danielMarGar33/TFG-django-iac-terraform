#!/bin/bash

# Cargar variables desde .env, ignorando líneas vacías y comentarios
while IFS='=' read -r key value; do
    # Ignora líneas vacías o que comienzan con #
    if [[ -z "$key" || "$key" =~ ^\s*# ]]; then
        continue
    fi

    # Quita espacios y exporta la variable
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    export "$key=$value"
done < .env
