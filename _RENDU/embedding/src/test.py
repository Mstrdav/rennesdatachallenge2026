from shiny import App, ui, render, reactive
import pandas as pd
import plotly.graph_objects as go

# Données d'exemple (à remplacer par votre base de données)
products_data = pd.DataFrame({
    'product_id': [1, 2, 3, 4, 5],
    'name': ['Pomme', 'Fromage', 'Steak', 'Lait', 'Chocolat'],
    'co2_per_unit': [0.25, 2.5, 27.0, 1.2, 4.5],
    'category': ['Fruit', 'Produit laitier', 'Viande', 'Produit laitier', 'Confiserie'],
    'image_url': ['🍎', '🧀', '🥩', '🥛', '🍫']
})

MAX_CO2 = 100  # Limite maximale de CO2

app_ui = ui.page_fluid(
    ui.h1("🌍 Calculateur d'Empreinte Carbone"),
    
    ui.layout_sidebar(
        ui.page_sidebar(
            ui.h3("Sélectionnez vos produits"),
            ui.output_ui("product_buttons"),
            ui.hr(),
            ui.h4("Panier :"),
            ui.output_ui("cart_display"),
            width="30%"
        ),
        
        ui.panel_main(
            ui.row(
                ui.column(
                    6,
                    ui.card(
                        ui.h3("Total CO2"),
                        ui.output_text("total_co2"),
                        ui.output_ui("progress_bar")
                    )
                ),
                ui.column(
                    6,
                    ui.card(
                        ui.h3("Répartition par catégorie"),
                        ui.output_plot("category_chart")
                    )
                )
            ),
            
            ui.row(
                ui.column(
                    12,
                    ui.card(
                        ui.h3("Évolution du total"),
                        ui.output_plot("evolution_chart")
                    )
                )
            ),
            
            ui.button("Réinitialiser", id="reset_btn", class_="btn-danger btn-lg")
        )
    )
)

def server(input, output, session):
    # État réactif pour le panier
    cart = reactive.Value({})  # {product_id: count}
    co2_history = reactive.Value([0])
    
    @render.ui
    def product_buttons():
        buttons = []
        for _, row in products_data.iterrows():
            buttons.append(
                ui.input_action_button(
                    f"prod_{row['product_id']}",
                    f"{row['image_url']} {row['name']}\n({row['co2_per_unit']}kg CO2)",
                    class_="btn-primary m-2",
                    style="width: 150px; height: 80px;"
                )
            )
        return ui.div(*buttons, class_="d-flex flex-wrap")
    
    # Gérer les clics sur les produits
    for _, row in products_data.iterrows():
        @reactive.Effect
        @reactive.event(input[f"prod_{row['product_id']}"])
        def add_product(product_id=row['product_id'], co2=row['co2_per_unit']):
            current_total = calculate_total_co2()
            
            # Vérifier la limite
            if current_total + co2 <= MAX_CO2:
                new_cart = cart.get().copy()
                new_cart[product_id] = new_cart.get(product_id, 0) + 1
                cart.set(new_cart)
                
                # Ajouter à l'historique
                new_history = co2_history.get() + [current_total + co2]
                co2_history.set(new_history)
    
    def calculate_total_co2():
        current_cart = cart.get()
        total = 0
        for product_id, count in current_cart.items():
            co2 = products_data[products_data['product_id'] == product_id]['co2_per_unit'].values[0]
            total += co2 * count
        return total
    
    @render.text
    def total_co2():
        total = calculate_total_co2()
        percentage = (total / MAX_CO2) * 100
        return f"{total:.2f} kg CO2 / {MAX_CO2} kg ({percentage:.1f}%)"
    
    @render.ui
    def progress_bar():
        total = calculate_total_co2()
        percentage = min((total / MAX_CO2) * 100, 100)
        color = "success" if percentage < 50 else "warning" if percentage < 80 else "danger"
        
        return ui.div(
            ui.tags.div(
                ui.tags.div(
                    f"{percentage:.1f}%",
                    class_=f"progress-bar progress-bar-{color}",
                    style=f"width: {percentage}%"
                ),
                class_="progress"
            )
        )
    
    @render.ui
    def cart_display():
        current_cart = cart.get()
        if not current_cart:
            return ui.p("Panier vide", class_="text-muted")
        
        items = []
        for product_id, count in current_cart.items():
            product = products_data[products_data['product_id'] == product_id].iloc[0]
            co2_total = product['co2_per_unit'] * count
            items.append(
                ui.p(
                    f"{product['name']} x{count}: {co2_total:.2f} kg CO2",
                    class_="mb-2"
                )
            )
        return ui.div(*items)
    
    @render.plot
    def category_chart():
        current_cart = cart.get()
        if not current_cart:
            return None
        
        category_co2 = {}
        for product_id, count in current_cart.items():
            product = products_data[products_data['product_id'] == product_id].iloc[0]
            category = product['category']
            co2 = product['co2_per_unit'] * count
            category_co2[category] = category_co2.get(category, 0) + co2
        
        fig = go.Figure(data=[
            go.Pie(labels=list(category_co2.keys()), values=list(category_co2.values()))
        ])
        fig.update_layout(title="CO2 par catégorie", height=400)
        return fig
    
    @render.plot
    def evolution_chart():
        history = co2_history.get()
        fig = go.Figure(data=[
            go.Scatter(y=history, mode='lines+markers', name='CO2 total')
        ])
        fig.add_hline(y=MAX_CO2, line_dash="dash", line_color="red", annotation_text="Limite")
        fig.update_layout(
            title="Évolution du CO2",
            xaxis_title="Ajout",
            yaxis_title="CO2 (kg)",
            height=400
        )
        return fig
    
    @reactive.Effect
    @reactive.event(input.reset_btn)
    def reset():
        cart.set({})
        co2_history.set([0])

app = App(app_ui, server)

