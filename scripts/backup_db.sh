#!/bin/bash

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT=$(readlink -f "${SCRIPT_DIR}/..")
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Database Configs
POSTGRES_USER="xalpha"
POSTGRES_DB_NAME="xalpha"
POSTGRES_SERVICE="postgres"

# Table Groups
NEWS_TABLES="-t news_articles -t sentiment_scores"
# Exclude news tables from "financial" backup
FINANCIAL_EXCLUDES="-T news_articles -T sentiment_scores"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log_message() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1"
}

usage() {
    echo "Usage: ./backup_db.sh [type]"
    echo "  type: 'full' (default), 'news', or 'financial'"
    exit 1
}

backup_postgres() {
    local type="${1:-full}"
    local backup_file="${BACKUP_DIR}/${type}_${TIMESTAMP}.sql.gz"
    local dump_opts=""
    
    case "$type" in
        "full")
            dump_opts=""
            ;;
        "news")
            dump_opts="$NEWS_TABLES"
            ;;
        "financial")
            dump_opts="$FINANCIAL_EXCLUDES"
            ;;
        *)
            log_message "Error: Unknown backup type '$type'"
            usage
            ;;
    esac

    log_message "Starting $type PostgreSQL backup..."
    
    local container_id=$(docker compose ps -q "$POSTGRES_SERVICE" | head -n 1)
    if [ -z "$container_id" ]; then
        log_message "Error: PostgreSQL container not found!"
        return 1
    fi
    
    local temp_file="${backup_file%.gz}"
    
    if docker exec "$container_id" pg_dump -U "$POSTGRES_USER" $dump_opts "$POSTGRES_DB_NAME" > "$temp_file"; then
        if [ ! -s "$temp_file" ]; then
             log_message "Error: PostgreSQL backup produced empty file!"
             rm -f "$temp_file"
             return 1
        fi
        gzip -f "$temp_file"
        log_message "PostgreSQL $type backup successful: $backup_file"
        # Cleanup old backups of the same type
        find "$BACKUP_DIR" -type f -name "${type}_*.sql.gz" -mtime +${RETENTION_DAYS} -exec rm {} \;
    else
        log_message "Error: PostgreSQL backup failed!"
        rm -f "$temp_file"
        return 1
    fi
}

main() {
    local type="$1"
    log_message "Starting Xalpha Backup Process..."
    log_message "Project Root: $PROJECT_ROOT"
    backup_postgres "$type"
}

main "$@"
