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
    echo "  The script will detect if it's a 'full', 'news', 'financial', 'debate', or 'portfolio' backup based on the filename."
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
    elif [[ $filename == reports_* ]]; then
        type="reports"
    elif [[ $filename == news_* ]]; then
        type="news"
    elif [[ $filename == financial_* ]]; then
        type="financial"
    elif [[ $filename == debate_* ]]; then
        type="debate"
    elif [[ $filename == portfolio_* ]]; then
        type="portfolio"
    else
        echo "Warning: Extension-based type detection failed. Assuming generic/full."
        type="full"
    fi

    confirm "$type"
    
    echo "Starting PostgreSQL $type restore..."
    
    if [ "$type" == "full" ]; then
        echo "Resetting public schema for FULL restore..."
        docker exec -i "$container_id" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    elif [ "$type" != "reports" ] && [ "$type" != "unknown" ]; then
        local tables=""
        case $type in
            news)
                tables="news_articles"
                ;;
            financial)
                tables="financial_reports, company_profiles, stock_eod, stock_trading_stats, commodity_prices, macro_indicators, market_index_stats, mutual_fund_nav"
                ;;
            debate)
                tables="debate_verdicts"
                ;;
            portfolio)
                tables="portfolio_positions, portfolio_suggestions"
                ;;
        esac

        if [ -n "$tables" ]; then
            echo "Truncating tables: $tables..."
            docker exec -i "$container_id" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB_NAME" -c "TRUNCATE TABLE $tables CASCADE;"
        fi
    fi
    
    if [ "$type" == "reports" ]; then
        echo "Restoring $type files..."
        tar -xzf "$BACKUP_FILE" -C "$(readlink -f "$SCRIPT_DIR/..")"
        echo "File $type restore completed!"
        return 0
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
