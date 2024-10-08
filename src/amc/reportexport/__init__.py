import csv
import logging

LOGGER = logging.getLogger(__name__)


def exportreport(export_file, cost_matrix, group_list, group_by_type):
    (export_file.parent).mkdir(parents=True, exist_ok=True)

    with open(export_file, "w", newline="") as ef:
        writer = csv.writer(ef)
        csv_header = list(cost_matrix.keys())
        csv_header.insert(0, "Month")

        writer.writerow(csv_header)

        months = list(cost_matrix.keys())

        if group_by_type == "account":
            for account in group_list:
                csv_row: list = []
                csv_row.append(account)
                for month in months:
                    csv_row.append(cost_matrix[month][account])
                writer.writerow(csv_row)
        elif group_by_type == "bu":
            bus = list(group_list.keys())
            bus.remove("ss")
            bus.extend(["total"])
            for bu in bus:
                csv_row: list = []
                csv_row.append(bu)
                for month in months:
                    csv_row.append(cost_matrix[month][bu])
                writer.writerow(csv_row)
        elif group_by_type == "service":
            for service in group_list:
                csv_row: list = []
                csv_row.append(service)
                for month in months:
                    if service in cost_matrix[month]:
                        csv_row.append(cost_matrix[month][service])
                writer.writerow(csv_row)
