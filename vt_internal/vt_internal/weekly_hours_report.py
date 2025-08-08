# Server Script (Type: Scheduled, Frequency: Weekly)
# Note: Schedule this to run on Mondays for the previous week.

import datetime
import frappe
from frappe.desk.query_report import run

def send_by_mail_weekly_hours_report():
  today = datetime.date.today()
  weekday = today.weekday()
  start_of_current_week = today - datetime.timedelta(days=weekday)
  end_of_current_week = start_of_current_week + datetime.timedelta(days=7)

  start_str = start_of_current_week.isoformat()
  end_str = end_of_current_week.isoformat()

  # Get all active employees
  employees = frappe.get_all(
      "Employee",
      filters={"status": "Active"},
      fields=["name", "user_id", "company"]
  )
  for emp in employees:
      # Determine employee email
      email = emp.user_id
      if not email:
          continue  # Skip if no email

      # Set filters for the report
      filters = {
          "employee": emp.name,
          "starts_on": start_str,
          "ends_on": end_str
      }

      # Run the report
      report_name = "Préparation des fiches de paie"
      report_data = run(report_name, filters=filters)
      if report_data["report_summary"][0]["value"] == 0: # Skip if no hours logged
         continue
      
      # Build HTML for the report
      html = ''
      html += '<p>Période : du {} au {}</p>'.format(start_str, end_str)
      html += '<style>table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid black; padding: 8px; text-align: left; }</style>'
      html += '<table>'
      html += '<thead><tr>'
      for col in report_data['columns']:
          label = col.get('label', col.get('fieldname'))
          width = col.get('width', 150)  # Default width if not set
          html += '<th style="width: {}px;">{}</th>'.format(width, label)
      html += '</tr></thead><tbody>'
      for row in report_data['result']:
          html += '<tr>'
          for col in report_data['columns']:
              label =  col.get('fieldname')
              html += '<td>{}</td>'.format(row[label])
          html += '</tr>'
      html += '</tbody></table>'
      
      # Send email
      subject = "Rapport hebdomadaire des heures"
      message = f"""Bonjour,<br><br>Voici votre rapport pour la semaine du {start_str} au {end_str}.<br><br>{html}<br><br>Cordialement."""
      frappe.sendmail(
          recipients=[email],
          subject=subject,
          message=message,
      )
