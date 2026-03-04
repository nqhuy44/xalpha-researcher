#!/bin/bash

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Database Configs
POSTGRES_USER="xalpha"
POSTGRES_DB_NAME="xalpha"
POSTGRES_SERVICE="postgres"

# Inputs
BACKUP_FILE="$1"

usage() {
    echo "Usage: ./restore_db.sh <backup_file>"
    echo "  <backup_file>: Path to the postgres backup file (.sql.gz)"
    echo "  The script will detect if it's a 'full', 'news', or 'financial' backup based on the filename."
    exit 1
}

if [ -z "$BACKUP_FILE" ]; then
    usage
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found at $BACKUP_FILE"
    exit 1
fi

confirm() {
    local type="$1"
    echo "WARNING: This will overwrite data in the 'xalpha' database."
    if [ "$type" == "full" ]; then
        echo "CAUTION: This is a FULL restore. It will DROP the 'public' schema first!"
    fi
    echo "Target File: $BACKUP_FILE"
    echo "Detected Type: $type"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restore cancelled."
        exit 1
    fi
}

restore_postgres() {
    local container_id=$(docker compose ps -q "$POSTGRES_SERVICE" | head -n 1)
    if [ -z "$container_id" ]; then
        echo "Error: PostgreSQL container not found!"
        exit 1
    fi
    
    # Detect type from filename (expected: full_*.sql.gz, news_*.sql.gz, financial_*.sql.gz)
    local filename=$(basename "$BACKUP_FILE")
    local type="unknown"
    if [[ $filename == full_* ]]; then
        type="full"
    elif [[ $filename == news_* ]]; then
        type="news"
    elif [[ $filename == financial_* ]]; then
        type="financial"
    else
        echo "Warning: Extension-based type detection failed. Assuming generic/full."
        type="full"
    fi

    confirm "$type"
    
    echo "Starting PostgreSQL $type restore..."
    
    if [ "$type" == "full" ]; then
        echo "Resetting public schema for FULL restore..."
        docker exec -i "$container_id" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    fi
    
    echo "Importing data..."
    if command -v gzcat >/dev/null 2>&1; then
        ZCAT="gzcat"
    else
        ZCAT="zcat"
    fi

    $ZCAT "$BACKUP_FILE" | docker exec -i "$container_id" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB_NAME"
    
    if [ $? -eq 0 ]; then
        echo "PostgreSQL $type restore completed successfully!"
    else
        echo "PostgreSQL $type restore failed!"
        exit 1
    fi
}

restore_postgres
