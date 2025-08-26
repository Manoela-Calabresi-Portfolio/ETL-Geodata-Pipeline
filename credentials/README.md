# 🔐 Database Credentials Management

## **Overview**

This directory contains database credentials for the ETL Geodata Pipeline. 
**NEVER commit actual credentials to git!** Only templates and examples are safe.

## **🚨 Security Warning**

- ⚠️ **`database_credentials.yaml` contains REAL passwords - NEVER commit to git!**
- ✅ **`database_credentials.template.yaml` is safe to commit (contains placeholders)**
- 🔒 **The `credentials/` directory is gitignored for security**

## **📋 Setup Instructions**

### **Step 1: Create Your Credentials File**
```bash
# Copy the template to create your actual credentials file
cp credentials/database_credentials.template.yaml credentials/database_credentials.yaml
```

### **Step 2: Fill In Your Credentials**
Edit `credentials/database_credentials.yaml` and replace:
- `YOUR_POSTGRES_PASSWORD_HERE` → Your actual PostgreSQL superuser password
- `etl_secure_password_2024` → A secure password for the ETL user

### **Step 3: Verify Git Ignore**
Ensure these lines are in your `.gitignore`:
```gitignore
# Database credentials - DO NOT COMMIT TO GIT!
credentials/
*.env
```

### **Step 4: Test Setup**
```bash
python setup_postgres_database.py
```

## **🔧 File Structure**

```
credentials/
├── README.md                           # This file (safe to commit)
├── database_credentials.template.yaml  # Template (safe to commit)
└── database_credentials.yaml          # Your credentials (NEVER commit!)
```

## **📊 Credentials Format**

```yaml
database:
  # PostgreSQL superuser (for setup)
  postgres:
    host: "localhost"
    port: 5432
    user: "postgres"
    password: "your_actual_password"
    
  # ETL Pipeline database (will be created)
  etl_pipeline:
    host: "localhost"
    port: 5432
    database: "etl_geodata_pipeline"
    user: "etl_user"
    password: "secure_etl_password"
```

## **🚀 Database Setup Process**

The setup script will:
1. ✅ Connect to PostgreSQL as superuser
2. ✅ Create `etl_geodata_pipeline` database
3. ✅ Create `etl_user` with secure password
4. ✅ Enable PostGIS extensions
5. ✅ Create schemas: `etl_pipeline`, `stuttgart`, `curitiba`
6. ✅ Grant appropriate privileges
7. ✅ Test connections
8. ✅ Update Stuttgart configuration automatically

## **🔍 Troubleshooting**

### **Common Issues**
- **"Credentials file not found"** → Create `database_credentials.yaml` from template
- **"Connection failed"** → Check PostgreSQL is running and password is correct
- **"PostGIS extension failed"** → May need to install PostGIS manually

### **Verification Commands**
```bash
# Check if credentials file exists
ls -la credentials/

# Verify git ignore
git status credentials/

# Test database connection
python setup_postgres_database.py
```

## **🔄 Updating Credentials**

If you need to change passwords:
1. Update `credentials/database_credentials.yaml`
2. Run `python setup_postgres_database.py` again
3. The script will update existing users/databases

## **📚 Best Practices**

- 🔒 **Use strong, unique passwords**
- 🔄 **Rotate passwords regularly**
- 📁 **Keep credentials file secure**
- 🚫 **Never share credentials in code or documentation**
- ✅ **Use environment variables in production**

## **🌐 Production Deployment**

For production environments:
- Use environment variables instead of files
- Implement proper secret management
- Use SSL connections
- Restrict database access to application servers only

---

**Remember: Security first! Keep your credentials safe and never commit them to version control.**

