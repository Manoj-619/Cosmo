With DNS settings configured, move on to setting up Nginx on your VM to serve the Docker application on port 8080 via your domain on port 80.

```bash
# Update the package list and install Nginx
sudo apt update
sudo apt install nginx
# Create a new server block configuration file for your site
sudo nano /etc/nginx/sites-available/api-dev.zavmo.ai
```

```
## Enable the site by linking it to the `sites-enabled` directory:**

sudo rm /etc/nginx/sites-enabled/api-dev.zavmo.ai
sudo ln -s /etc/nginx/sites-available/api-dev.zavmo.ai /etc/nginx/sites-enabled/   

## IMPORTANT: DELETE THE DEFAULT CONFIGURATION FILE
sudo rm /etc/nginx/sites-enabled/default

# Test the Nginx configuration for errors
### Restart Nginx to apply the changes
sudo nginx -t
sudo systemctl restart nginx
sudo ufw allow 'Nginx Full'
sudo ufw reload
cat /var/log/nginx/error.log
```

cat /var/log/nginx/error.log