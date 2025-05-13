# Anodot Automation

This repository contains automation scripts for Anodot services.

## Configuration Setup

1. Copy the template configuration file:
   ```bash
   cp config.ini.template config.ini
   ```

2. Edit `config.ini` and replace the placeholder values with your actual credentials:
   - `pileus_username`: Your Pileus username
   - `pileus_password`: Your Pileus password

⚠️ **Important**: Never commit your actual `config.ini` file to version control as it contains sensitive information.

## Security Note

The `config.ini` file contains sensitive credentials and is intentionally excluded from version control via `.gitignore`. Always keep your credentials secure and never share them publicly. 