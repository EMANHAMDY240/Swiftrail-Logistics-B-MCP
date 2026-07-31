 Swiftrail Logistics Data Layer(mysql)

files
schema.sql  tables 
seed.sql  (fixed test-input set)
erd.mmd  Relationship between tables


tables

employees موظفي الشركة، بدور naturally يحدد صلاحياتهم (sales_rep / finance_manager) 
customers بيانات العملاء وحالتهم الائتمانية (credit_status) 
shipments طلبات الشحن، مرتبطة بعميل وموظف طلبها 
invoices  الفواتير لكل شحنه
credit_holds  الحجوزات الائتمانية على العملاء، بدرجة خطورة (minor / severe) 
rate_exceptions طلبات الخصم على الشحنات، بحد أقصى 50% 


Relationship between tables
all relation are one to many 
exeption shipments and invoices is one to one


seed data 
- **Red Sea Steel Imports: عليها حجز `severity = severe` (متأخرة 90+ يوم) → المفروض تفعّل الـ elicitation في `release_credit_hold`
- **Nile Grain Traders: عليها حجز `severity = minor` → تتحل من غير توقف بشري
- **Rate exception على شحنة 500: خصم 25% (>15%) → المفروض يفعّل الـ elicitation في `approve_rate_exception`
- **Rate exception على شحنة 400: خصم 10% (≤15%) → يتوافق عليه تلقائيًا من غير توقف

