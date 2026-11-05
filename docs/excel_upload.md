# Native Excel upload

The uploader accepts `.csv` and `.xlsx` inputs. Excel uploads offer a worksheet selector. The selected worksheet goes through the existing source audit and manual/automatic column mapping. Original negative quantities and refund/cancellation rows are retained.

Use a data worksheet with column headers in the first row. Excel formulas are not recalculated by pandas/openpyxl; cells without saved cached results may import as missing. The upload handles `.xlsx` only; older `.xls` workbooks require conversion or a separately supported reader. For large Excel files, parsing may take longer and consume more memory than CSV.

UCI Online Retail example: map `InvoiceDate` to Date, `Description` to Item, `UnitPrice` to Price, `Quantity` to Units Sold, and `InvoiceNo` as an order/invoice identifier. The dataset does not supply actual unit costs or a matching independent settlement report. Set currency to GBP. Do not treat `InvoiceNo` as a unique event per line because it repeats for multi-item invoices.
