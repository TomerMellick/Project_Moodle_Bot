from bs4 import BeautifulSoup


def parse_html_table(html):
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html, 'html.parser')

    # Find the table element with the specified class
    table = soup.find('table', class_='GridView')

    # Initialize a list to store the extracted cell values
    cell_values = []

    # Iterate through each row in the table
    for row in table.find_all('tr'):
        # Find all cells in the row
        cells = row.find_all(['th', 'td'])

        # Extract and store the text content of each cell
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        cell_values.append(cell_texts)

    # Print the extracted cell values
    buttonsList = []
    for row in cell_values:
        buttonsList.append(row[1])
    buttonsList.pop(0)
    return buttonsList