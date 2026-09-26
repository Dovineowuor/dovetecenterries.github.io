# Update deployment checklist
cat > deployment_checklist.md << 'EOL'
# Zoobee-Cart Deployment Checklist

## Pre-Deployment Checklist

### Version Control
- [ ] Commit all changes to the repository
- [ ] Ensure all tests are passing

### Environment
- [x] Set up virtual environment
- [x] Install all dependencies from requirements.txt

## Database Setup
- [x] Configure Django to use MySQL in settings.py
- [x] Ensure MySQL database `zobenqxh_zobeestores` exists on hosting server
- [x] Ensure MySQL user `zobenqxh_Zobee` exists with correct permissions
- [x] Run migrations on the hosting server

## Environment Variables
- [x] Create .env file with production settings
- [x] Set secure SECRET_KEY
- [x] Configure database credentials
- [x] Set DEBUG to False

## Static and Media Files
- [x] Collect static files
- [x] Configure static files serving
- [x] Set up media files storage

## Security
- [x] Enable HTTPS
- [x] Set secure cookies
- [x] Configure allowed hosts

## Performance
- [ ] Set up caching
- [ ] Configure database connection pooling
- [ ] Optimize database queries

## Monitoring
- [ ] Set up logging
- [ ] Configure error tracking
- [ ] Set up performance monitoring

## Deployment Steps
1. Pull latest code
2. Activate virtual environment
3. Install dependencies
4. Run migrations
5. Collect static files
6. Restart web server

## Post-Deployment
- [ ] Verify application is running
- [ ] Test all critical paths
- [ ] Check error logs
- [ ] Perform security scan

## Rollback Plan
- [ ] Backup database before deployment
- [ ] Have a previous working version ready

## Notes
- Always test in staging environment first
- Monitor application performance after deployment