# Database Connection Troubleshooting

## Issue: "Can't connect to MySQL server on '10.248.48.202' (timed out)"

### Possible Causes:

1. **Network/Firewall Issue**: The VPS might not be able to reach the database server
2. **Database Server Not Running**: The MySQL server might be down
3. **Firewall Blocking Port 3306**: The database server's firewall might be blocking connections
4. **Wrong IP Address**: The IP might have changed or be incorrect

### Troubleshooting Steps:

#### 1. Test Network Connectivity

```bash
# Test if you can reach the database server
ping 10.248.48.202

# Test if port 3306 is accessible
telnet 10.248.48.202 3306
# OR
nc -zv 10.248.48.202 3306
```

#### 2. Check Database Credentials

Verify your `.env` file has the correct credentials:

```bash
cat /var/www/frl-python-api/.env
```

Make sure:
- `DB_HOST=10.248.48.202`
- `DB_USER=freerele_bwp`
- `DB_PASSWORD` is correct (with quotes if it contains special characters)
- `DB_NAME=freerele_blackwoodproductions`

#### 3. Test Database Connection Manually

```bash
# Install MySQL client if not already installed
dnf install mysql -y

# Test connection
mysql -h 10.248.48.202 -u freerele_bwp -p freerele_blackwoodproductions
```

#### 4. Check Firewall Rules

On the database server (10.248.48.202), make sure:
- MySQL is listening on the correct interface
- Firewall allows connections from your VPS IP
- MySQL user has permission to connect from your VPS IP

#### 5. Check if Database Server is Accessible from PHP App

If the PHP app on the same network can connect, check:
- Is the PHP app on the same server or different server?
- What IP does the PHP app use to connect?

#### 6. Temporary Workaround - Test with Local Connection

If you need to test the app without database access, you can temporarily modify the code to handle connection errors gracefully.

### Updated Code Features:

The updated `database.py` now:
- Uses **lazy connection** (only connects when needed, not at startup)
- Has **retry logic** (3 attempts with 2-second delays)
- Has **connection timeouts** (10 seconds)
- **Auto-reconnects** on connection errors

This means the app should start even if the database is temporarily unavailable, and will connect when you make your first API call.

### Next Steps:

1. **Test network connectivity** first (step 1 above)
2. **Verify credentials** in `.env` file
3. **Check with your network admin** if firewall rules need to be updated
4. **Try starting the app again** - it should start now even if DB is unavailable

