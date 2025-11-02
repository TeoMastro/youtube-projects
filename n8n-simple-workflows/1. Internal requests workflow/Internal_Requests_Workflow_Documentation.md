# Internal Requests Workflow Documentation

## Overview
This n8n workflow provides a complete internal request management system for organizations with multiple departments. It captures employee requests through a web form, processes and structures the data, routes submissions to the appropriate department, and logs everything in Google Sheets.

---

## 📋 Workflow Summary

**Workflow Name:** Internal Requests Workflow  
**Trigger Type:** Form Trigger (Webhook)  
**Status:** Active  
**Version ID:** c0a541f5-a238-468b-97a9-b9812faef43e

---

## 🔄 Workflow Architecture

```
┌─────────────────┐
│  Form Trigger   │  (Webhook URL: /form/internal-request)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Map Variables   │  (JavaScript Code Node)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Route by Dept   │  (Switch Node - 3 Outputs)
└────────┬────────┘
         │
    ┌────┴────┬─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────┐ ┌────────┐
│Acct.   │ │HR  │ │IT      │  (Google Sheets Nodes)
│Sheet   │ │    │ │Sheet   │
└────────┘ └────┘ └────────┘
```

---

## 📝 Node Details

### 1. Form Trigger Node

**Node Type:** `n8n-nodes-base.formTrigger`  
**Version:** 2  
**Webhook ID:** `internal-request-form`  
**Path:** `/internal-request`

#### Form Configuration

**Form Title:** Internal Request Form  
**Form Description:** Submit your request to the appropriate department

#### Form Fields

| Field Label | Field Type | Required | Options |
|------------|------------|----------|---------|
| Your Name | Text | ✅ Yes | - |
| Email | Email | ✅ Yes | - |
| Department | Dropdown | ✅ Yes | Accounting, HR, IT |
| Request Title | Text | ✅ Yes | - |
| Request Description | Textarea | ✅ Yes | - |
| Priority | Dropdown | ✅ Yes | Low, Medium, High, Urgent |

#### Output Format
```json
{
  "Your Name": "string",
  "Email": "email@domain.com",
  "Department": "Accounting|HR|IT",
  "Request Title": "string",
  "Request Description": "string",
  "Priority": "Low|Medium|High|Urgent",
  "submittedAt": "ISO timestamp",
  "formMode": "test|production"
}
```

---

### 2. Map Variables Node

**Node Type:** `n8n-nodes-base.code`  
**Version:** 2  
**Language:** JavaScript

#### Purpose
Transforms raw form data into a structured format with additional metadata.

#### Code Logic
```javascript
// Map and structure the form data
const formData = $input.item.json;

// Extract timestamp
const timestamp = new Date().toISOString();

// Map variables from form submission
// The form uses "Your Name", "Email", etc. as keys
const mappedData = {
  timestamp: timestamp,
  requester_name: formData['Your Name'] || formData.requester_name,
  requester_email: formData['Email'] || formData.requester_email,
  department: formData['Department'] || formData.department,
  request_title: formData['Request Title'] || formData.request_title,
  request_description: formData['Request Description'] || formData.request_description,
  priority: formData['Priority'] || formData.priority,
  status: 'New',
  request_id: `REQ-${Date.now()}`
};

// Return the mapped data
return {
  json: mappedData
};
```

#### Transformations
- **Adds Timestamp:** Current date/time in ISO format
- **Generates Request ID:** Format `REQ-{timestamp}` (e.g., REQ-1762106268595)
- **Sets Initial Status:** Always "New"
- **Normalizes Field Names:** Converts form labels to snake_case keys

#### Output Format
```json
{
  "timestamp": "2025-11-02T17:57:48.595Z",
  "requester_name": "John Doe",
  "requester_email": "john@company.com",
  "department": "HR",
  "request_title": "New Equipment Request",
  "request_description": "Need a new laptop for development",
  "priority": "Medium",
  "status": "New",
  "request_id": "REQ-1762106268595"
}
```

---

### 3. Route by Department Node

**Node Type:** `n8n-nodes-base.switch`  
**Version:** 3

#### Purpose
Routes requests to the appropriate Google Sheet based on department selection.

#### Routing Rules

| Output | Condition | Destination |
|--------|-----------|-------------|
| 1 (Accounting) | `department` equals "Accounting" | Add to Accounting Sheet |
| 2 (HR) | `department` equals "HR" | Add to HR Sheet |
| 3 (IT) | `department` equals "IT" | Add to IT Sheet |

#### Configuration
- **Case Sensitive:** Yes
- **Type Validation:** Strict
- **Combinator:** AND
- **Outputs Renamed:** Yes (Accounting, HR, IT)

---

### 4. Google Sheets Nodes (3 nodes)

**Node Type:** `n8n-nodes-base.googleSheets`  
**Version:** 4.4  
**Operation:** Append or Update  
**Credentials ID:** `ZKEuSXNi8Hoc2dz7`

#### Common Configuration

**Spreadsheet ID:** `1FcK4Cjo2iZEiPnqa0067WNWhDRe0p5vNiImZE2ZUjBE`

#### Sheet Names
1. **Add to Accounting Sheet** → Sheet name: "Accounting"
2. **Add to HR Sheet** → Sheet name: "HR"
3. **Add to IT Sheet** → Sheet name: "IT"

#### Column Mapping

All three nodes write data to the same columns:

| Column Header | Mapped Value | Type |
|--------------|--------------|------|
| Timestamp | `{{ $json.timestamp }}` | String |
| Request ID | `{{ $json.request_id }}` | String |
| Requester Name | `{{ $json.requester_name }}` | String |
| Requester Email | `{{ $json.requester_email }}` | String |
| Request Title | `{{ $json.request_title }}` | String |
| Description | `{{ $json.request_description }}` | String |
| Priority | `{{ $json.priority }}` | String |
| Status | `{{ $json.status }}` | String |

#### Matching Column
- **Request ID** is used as the unique identifier for append/update operations

#### Options
- **Attempt to Convert Types:** No
- **Convert Fields to String:** No

---

## 🗂️ Google Sheets Setup

### Spreadsheet Structure

**One Google Spreadsheet with Three Sheets:**

#### Required Sheet Names (case-sensitive):
1. Accounting
2. HR
3. IT

#### Column Headers (Row 1 in each sheet):

| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| Timestamp | Request ID | Requester Name | Requester Email | Request Title | Description | Priority | Status |

### Sample Data Format

```
Timestamp                  | Request ID          | Requester Name | Requester Email      | Request Title        | Description              | Priority | Status
2025-11-02T17:57:48.595Z  | REQ-1762106268595  | Jane Smith     | jane@company.com     | Software License     | Need Adobe CC license    | High     | New
2025-11-02T18:10:22.341Z  | REQ-1762107022341  | John Doe       | john@company.com     | Vacation Request     | 2 weeks in December      | Medium   | New
```

---

## 🔐 Credentials & Authentication

### Google Sheets OAuth2 API

**Credential Name:** Google Sheets account  
**Credential ID:** `ZKEuSXNi8Hoc2dz7`

#### Required Permissions:
- Read access to spreadsheet metadata
- Write access to append/update rows
- Access to the specific spreadsheet

#### Setup Steps:
1. Create Google Cloud Project
2. Enable Google Sheets API
3. Create OAuth2 credentials
4. Configure authorized redirect URIs
5. Authenticate in n8n

---

## 🚀 How to Use

### For End Users (Employees)

1. **Access the Form**
   - Navigate to: `https://your-n8n-instance.com/form/internal-request`
   - Or use the Test URL during development

2. **Fill Out the Form**
   - Enter your name and email
   - Select your department (Accounting, HR, or IT)
   - Enter request title and description
   - Choose priority level
   - Submit

3. **Confirmation**
   - You'll see a success message upon submission
   - Your request is automatically routed to the appropriate department

### For Administrators

1. **Monitor Requests**
   - Open the Google Spreadsheet
   - Click on the appropriate department tab
   - View all incoming requests with timestamps

2. **Update Status**
   - Manually update the "Status" column as requests are processed
   - Common statuses: New, In Progress, Completed, Cancelled

3. **Track Metrics**
   - Sort by Priority to handle urgent requests first
   - Filter by Requester Email to see user activity
   - Use Request ID for unique identification

---

## 📊 Data Flow Example

### Input (Form Submission)
```json
{
  "Your Name": "Alice Johnson",
  "Email": "alice@company.com",
  "Department": "IT",
  "Request Title": "Password Reset",
  "Request Description": "Cannot access email account",
  "Priority": "Urgent"
}
```

### Processing (After Map Variables)
```json
{
  "timestamp": "2025-11-02T18:30:15.123Z",
  "requester_name": "Alice Johnson",
  "requester_email": "alice@company.com",
  "department": "IT",
  "request_title": "Password Reset",
  "request_description": "Cannot access email account",
  "priority": "Urgent",
  "status": "New",
  "request_id": "REQ-1762108215123"
}
```

### Output (Google Sheet Row)
```
2025-11-02T18:30:15.123Z | REQ-1762108215123 | Alice Johnson | alice@company.com | Password Reset | Cannot access email account | Urgent | New
```

---

## 🔧 Customization Guide

### Adding New Departments

1. **Update Form Trigger**
   - Add new option to Department dropdown
   ```json
   {
     "option": "Finance"
   }
   ```

2. **Update Switch Node**
   - Add new routing rule
   - Set condition: `{{ $json.department }}` equals "Finance"
   - Rename output to "Finance"

3. **Create New Sheet**
   - Add "Finance" tab to Google Spreadsheet
   - Add column headers

4. **Add Google Sheets Node**
   - Create new node "Add to Finance Sheet"
   - Connect to Switch output
   - Configure same column mappings

### Adding New Form Fields

1. **Update Form Trigger**
   ```json
   {
     "fieldLabel": "Cost Center",
     "fieldType": "text",
     "requiredField": false
   }
   ```

2. **Update Map Variables Code**
   ```javascript
   const mappedData = {
     // ... existing fields
     cost_center: formData['Cost Center'] || formData.cost_center,
   };
   ```

3. **Update Google Sheets Columns**
   - Add "Cost Center" header to all sheets
   - Update column mapping in all Google Sheets nodes
   ```json
   "Cost Center": "={{ $json.cost_center }}"
   ```

### Changing Priority Levels

Modify the Priority dropdown options in Form Trigger:
```json
{
  "option": "Critical"
},
{
  "option": "High"
},
{
  "option": "Normal"
},
{
  "option": "Low"
}
```

---