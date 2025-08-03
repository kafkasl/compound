run:
    uvicorn main:app --reload

deploy:
    plash_deploy

view:
    plash_view

start:
    plash_start

stop:
    plash_stop

logs:
    plash_logs

db-habits:
    sqlite3 -header -csv data/habits.db "SELECT * FROM habits;"
db-users:
    sqlite3 -header -csv data/habits.db "SELECT * FROM users;"

db-clear-entries:
    sqlite3 data/habits.db "DELETE FROM entries;"

download:
    plash_download 

sync-prod-db:
    rm -rf download
    plash_download
    sqlite3 habits-prod.db "PRAGMA wal_checkpoint(FULL); VACUUM;" 
    rm -rf data download/data/habits.db* download/data/habits-prod.db-shm download/data/monitoring-prod.db-wal
    mv download/data .
    mv data/habits-prod.db data/habits.db
