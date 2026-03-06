from models.rag_model import search_all_knowledge, get_recommendations
from transformers import pipeline
import torch
import json
import re
from urllib.parse import quote_plus
from models.speech_to_text import transcribe_audio

# Load text generation pipeline for intelligent responses
try:
    generator = pipeline(
        "text2text-generation",
        model="google/flan-t5-base",
        device=0 if torch.cuda.is_available() else -1
    )
except:
    generator = None


class TravelChatAgent:
    """AI Agent for handling travel-related queries"""
    
    def __init__(self):
        self.conversation_history = []
        self.context = {"pending_route": None}
    
    def classify_query(self, message):
        """Classify the type of query"""
        message_lower = message.lower()
        
        # Define keywords for different categories
        destinations_keywords = ['where', 'destination', 'place', 'visit', 'located', 'find']
        route_keywords = ['route', 'direction', 'how to get', 'travel from', 'way to', 'path']
        guide_keywords = ['guide', 'tour', 'guide me', 'recommend guide', 'experienced']
        hotel_keywords = ['hotel', 'stay', 'accommodation', 'resort', 'lodge', 'rooms']
        vehicle_keywords = ['vehicle', 'car', 'transport', 'bus', 'train', 'taxi', 'book ride']
        hospital_keywords = ['hospital', 'doctor', 'medical', 'emergency', 'health', 'clinic']
        trip_keywords = ['trip', 'plan', 'itinerary', 'days', 'when', 'best time']
        tourism_keywords = ['attraction', 'tourist', 'heritage', 'adventure', 'nature', 'culture', 'heritage site', 'tea estate']
        route_keywords = ['route', 'direction', 'how to get', 'travel from', 'way to', 'path', 'to', 'from']
        
        query_type = 'general'
        
        for keyword in destinations_keywords:
            if keyword in message_lower:
                query_type = 'destinations'
                break
        
        for keyword in route_keywords:
            if keyword in message_lower:
                query_type = 'routes'
                break
        
        for keyword in guide_keywords:
            if keyword in message_lower:
                query_type = 'guides'
                break
        
        for keyword in hotel_keywords:
            if keyword in message_lower:
                query_type = 'hotels'
                break
        
        for keyword in vehicle_keywords:
            if keyword in message_lower:
                query_type = 'vehicles'
                break
        
        for keyword in hospital_keywords:
            if keyword in message_lower:
                query_type = 'hospitals'
                break
        
        for keyword in trip_keywords:
            if keyword in message_lower:
                query_type = 'trip_planning'
                break
        
        for keyword in tourism_keywords:
            if keyword in message_lower:
                query_type = 'tourism'
                break
        
        return query_type
    
    def search_knowledge_base(self, message):
        """Search the knowledge base for relevant information"""
        try:
            raw = search_all_knowledge(message)

            # search_all_knowledge returns a list of items with keys: type, data
            # Normalize into dict expected by the response handlers
            grouped = {
                'destinations': [],
                'guides': [],
                'vehicles': [],
                'drivers': [],
                'bookings': [],
                'hotels': [],
                'hospitals': [],
                'tourism': [],
                'routes': []
            }

            if isinstance(raw, dict):
                # already grouped
                return raw

            for item in raw or []:
                t = item.get('type')
                data = item.get('data') or {}
                if not t:
                    continue
                key = t + 's' if not t.endswith('s') else t
                if key in grouped:
                    grouped[key].append(data)
                else:
                    grouped[key] = grouped.get(key, []) + [data]

            return grouped
        except Exception as e:
            # Log to console for debugging (server logs)
            print(f"search_knowledge_base error: {e}")
            return {
                'destinations': [],
                'guides': [],
                'vehicles': [],
                'drivers': [],
                'bookings': [],
                'hotels': [],
                'hospitals': [],
                'tourism': [],
                'routes': []
            }
    
    def generate_response(self, message, query_type, search_results):
        """Generate an intelligent response based on query type and search results"""
        
        # Create context-aware prompts
        if query_type == 'destinations':
            return self.handle_destinations_query(message, search_results)
        elif query_type == 'routes':
            return self.handle_routes_query(message, search_results)
        elif query_type == 'guides':
            return self.handle_guides_query(message, search_results)
        elif query_type == 'hotels':
            return self.handle_hotels_query(message, search_results)
        elif query_type == 'vehicles':
            return self.handle_vehicles_query(message, search_results)
        elif query_type == 'hospitals':
            return self.handle_hospitals_query(message, search_results)
        elif query_type == 'tourism':
            return self.handle_tourism_query(message, search_results)
        elif query_type == 'trip_planning':
            return self.handle_trip_planning_query(message, search_results)
        else:
            return self.handle_general_query(message, search_results)
    
    def handle_destinations_query(self, message, results):
        """Handle destination-related queries"""
        destinations = results.get('destinations', [])
        
        if not destinations:
            return "I couldn't find specific destinations matching your query. Try asking about popular places like 'Sigiriya', 'Kandy', 'Mirissa', or 'Ella'!"
        
        response = "Here are some amazing destinations for you:\n\n"
        for dest in destinations[:3]:  # Show top 3
            name = dest.get('name', 'Unknown')
            district = dest.get('district', '')
            description = dest.get('description', dest.get('summary', ''))[:100]
            response += f"**{name}** ({district})\n{description}...\n\n"
        
        return response
    
    def handle_routes_query(self, message, results):
        message_lower = message.lower()

        # Detect travel method (expanded)
        methods = {
            'drive': 'driving',
            'car': 'driving',
            'vehicle': 'driving',
            'train': 'transit',
            'bus': 'transit',
            'public': 'transit',
            'walk': 'walking',
            'bicycle': 'bicycling',
            'bike': 'bicycling'
        }

        selected_method = None
        for key in methods:
            if key in message_lower:
                selected_method = methods[key]
                break

        # If user selected method and route is waiting
        if selected_method and self.context.get("pending_route"):
            route = self.context["pending_route"]
            self.context["pending_route"] = None

            start = route["start"]
            end = route["end"]
            stops = route["stops"]

            # Build via text
            via_text = ""
            if stops:
                via_text = " via " + " → ".join(stops)

            # Build directions path
            directions_path = quote_plus(start)

            if stops:
                for stop in stops:
                    directions_path += f"/{quote_plus(stop)}"

            directions_path += f"/{quote_plus(end)}"

            # Full navigation URL with travel mode (FREE)
            maps_url = (
                f"https://www.google.com/maps/dir/{directions_path}"
                f"?travelmode={selected_method}"
            )

            # Embed map (simple query preview – free)
            query_preview = f"{start} to {end}"
            if stops:
                query_preview = f"{start} to " + " to ".join(stops) + f" to {end}"

            maps_embed = (
                f"https://maps.google.com/maps"
                f"?saddr={quote_plus(start)}"
                f"&daddr={quote_plus(end)}"
                f"&output=embed"
            )

            # Travel mode display text
            mode_text = {
                'driving': 'Driving',
                'transit': 'Public Transport (Train/Bus)',
                'walking': 'Walking',
                'bicycling': 'Bicycling'
            }.get(selected_method, 'Driving')

            response = f"""
    Route: **{start} → {end}**{via_text}

    <div style="width:100%; height:320px; margin-top:8px; margin-bottom:8px;">
    <iframe
        width="100%"
        height="100%"
        style="border:0; border-radius:12px;"
        loading="lazy"
        allowfullscreen
        src="{maps_embed}">
    </iframe>
    </div>

    Open full navigation:
    {maps_url}

    Travel Mode: **{mode_text}**

    Would you like:
    • Estimated travel time  
    • Vehicle recommendations  
    • Nearby attractions on the way?
    """
            return response

        # Otherwise extract route from message
        start, end, stops = self.extract_locations(message)

        if not start or not end:
            return (
                "Tell me your route like:\n"
                "• Colombo to Kandy\n"
                "• Ella to Mirissa via Nuwara Eliya"
            )

        # Save route and ask method
        self.context["pending_route"] = {
            "start": start,
            "end": end,
            "stops": stops
        }

        via_text = ""
        if stops:
            via_text = " via " + " → ".join(stops)

        return (
            f"Route detected: **{start} → {end}**{via_text}\n\n"
            "Which travel method would you prefer?\n"
            "• Drive\n"
            "• Train / Bus\n"
            "• Walk\n"
            "• Bicycle"
        )
    
    def generate_route_response(self, start, end, stops, method):
        travel_mode = "driving"

        if method in ['train']:
            travel_mode = "transit"
        elif method in ['bus']:
            travel_mode = "transit"

        # Waypoints
        waypoints = ""
        if stops:
            waypoints = "&waypoints=" + "|".join([quote_plus(s) for s in stops])

        # Google Maps URL
        maps_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote_plus(start)}"
            f"&destination={quote_plus(end)}"
            f"&travelmode={travel_mode}"
            f"{waypoints}"
        )

        # Embedded iframe
        embed_url = maps_url.replace("/dir/?api=1", "/embed/v1/directions?key=YOUR_GOOGLE_MAPS_API_KEY")

        stops_text = ""
        if stops:
            stops_text = "\nStops: " + " → ".join(stops)

        response = f"""
    🗺 Route Plan

    **{start} → {end}**
    Method: {method.title()}
    {stops_text}

    Estimated Time:
    • Drive: Depends on traffic
    • Train/Bus: Based on schedule

    <iframe
        width="100%"
        height="250"
        style="border:0; border-radius:12px;"
        loading="lazy"
        allowfullscreen
        src="{embed_url}">
    </iframe>

    Open in Google Maps:
    {maps_url}

    Would you like vehicle booking for this route?
    """

        return response
        
    def handle_guides_query(self, message, results):
        """Handle tour guide queries"""
        guides = results.get('guides', [])
        
        if not guides:
            return "No guides found matching your criteria. I can help you find experienced tour guides for your trip! Tell me the destination or type of tour you're interested in."
        
        response = "Here are experienced guides available:\n\n"
        for guide in guides[:3]:
            name = guide.get('name', 'Guide')
            experience = guide.get('experience', '0')
            specialization = guide.get('specialization', 'General tours')
            response += f"• **{name}** - {experience}+ years in {specialization}\n"
        
        response += "\nContact them directly to book or ask for recommendations!"
        return response
    
    def handle_hotels_query(self, message, results):
        """Handle accommodation queries"""
        hotels = results.get('hotels', [])
        
        if not hotels:
            return "I'm searching for accommodations! Please tell me:\n• Where would you like to stay?\n• What's your budget?\n• Any specific amenities you need?"
        
        response = "Great hotels and resorts for you:\n\n"
        for hotel in hotels[:3]:
            name = hotel.get('name', 'Hotel')
            price = hotel.get('price_per_night', 'Contact for price')
            district = hotel.get('district', '')
            amenities = ', '.join(hotel.get('amenities', [])[:2])
            response += f"• **{name}** ({district})\n  LKR {price}/night\n  Amenities: {amenities}\n\n"
        
        return response
    
    def handle_vehicles_query(self, message, results):
        """Handle vehicle/transportation booking queries"""
        vehicles = results.get('vehicles', [])
        
        if not vehicles:
            return "What type of vehicle would you like to book?\n• Car\n• Van\n• Mini bus\n• Tuk-tuk\nTell me your destination and dates!"
        
        response = "Available vehicles for booking:\n\n"
        for vehicle in vehicles[:3]:
            vehicle_type = vehicle.get('type', 'Vehicle')
            seats = vehicle.get('seats', '4')
            fare = vehicle.get('estimated_fare', 'Contact for quote')
            response += f"• {vehicle_type} ({seats} seats) - LKR {fare}\n"
        
        response += "\nReady to book? Provide your travel dates and route!"
        return response
    
    def handle_hospitals_query(self, message, results):
        """Handle medical/hospital queries"""
        hospitals = results.get('hospitals', [])
        
        if not hospitals:
            return "Emergency? I can help you find medical facilities!\n\nNo hospitals found in search. Please tell me:\n• Your current location\n• Type of medical emergency\n• Preferred hospital (if any)"
        
        response = "Nearby medical facilities:\n\n"
        for hospital in hospitals[:3]:
            name = hospital.get('name', 'Hospital')
            district = hospital.get('district', '')
            services = ', '.join(hospital.get('services', ['General care'])[:2])
            response += f"• **{name}** ({district})\n  Services: {services}\n\n"
        
        response += "For emergencies, call immediately! Emergency contact: +94-011-2696291"
        return response
    
    def handle_trip_planning_query(self, message, results):
        """Handle trip planning queries"""
        destinations = results.get('destinations', [])
        
        response = "**Trip Planning Guide for Sri Lanka**\n\n"
        response += "**Best Time to Visit:**\n"
        response += "• West/South Coast: Nov-Feb (Dry season)\n"
        response += "• East Coast: May-Sept (Dry season)\n"
        response += "• upcountry/Central: Year-round\n\n"
        
        response += "**Recommended Duration:**\n"
        response += "• 3-4 days: Coastal highlights\n"
        response += "• 7-10 days: Complete island tour\n"
        response += "• 2+ weeks: In-depth exploration\n\n"
        
        if destinations:
            response += "**Popular Destinations to Include:**\n"
            for dest in destinations[:4]:
                response += f"• {dest.get('name', 'Destination')} ({dest.get('district', '')})\n"
        
        response += "\nWould you like me to suggest a specific itinerary?"
        return response
    
    def handle_tourism_query(self, message, results):
        """Handle tourism/attraction queries"""
        tourism = results.get('tourism', [])
        q_lower = message.lower()
        
        if not tourism:
            return "I couldn't find tourism attractions matching your query. Try asking about:\n• Natural attractions (waterfalls, beaches, national parks)\n• Heritage sites (temples, forts, ancient ruins)\n• Adventure activities (hiking, diving, wildlife)\n• Cultural experiences (tea estates, local villages)"

        # choose an intro based on keywords
        intro = "🎯 **Tourist Attractions & Experiences**\n\n"
        if 'waterfall' in q_lower:
            intro = "💧 Looking for waterfalls? Here are the top spots:\n\n"
        elif 'temple' in q_lower or 'heritage' in q_lower or 'fort' in q_lower:
            intro = "🏯 Heritage and cultural sites you might love:\n\n"
        elif 'tea' in q_lower:
            intro = "🍃 Explore tea estates and spice gardens:\n\n"
        elif 'beach' in q_lower or 'snorkel' in q_lower or 'diving' in q_lower:
            intro = "🏖 Beach and water activities to consider:\n\n"
        elif 'hike' in q_lower or 'park' in q_lower or 'nature' in q_lower:
            intro = "🌲 Nature and adventure attractions ahead:\n\n"
        elif 'ayurveda' in q_lower or 'spa' in q_lower or 'wellness' in q_lower:
            intro = "🧘 Wellness and Ayurveda spots for relaxation:\n\n"
        # additional boosts for matching categories
        keyword_category_map = {
            'cultural': 'Cultural & Heritage Sites',
            'heritage': 'Cultural & Heritage Sites',
            'temple': 'Cultural & Heritage Sites',
            'fort': 'Cultural & Heritage Sites',
            'nature': 'Nature & Adventure',
            'waterfall': 'Nature & Adventure',
            'hike': 'Nature & Adventure',
            'park': 'Nature & Adventure',
            'beach': 'Nature & Adventure',
            'tea': 'Tea & Spice Shops',
            'spice': 'Tea & Spice Shops',
            'food': 'Authentic Food Places',
            'restaurant': 'Authentic Food Places',
            'experience': 'Local Experiences',
            'cooking': 'Local Experiences',
            'village': 'Local Experiences',
            'ayurveda': 'Ayurveda & Wellness',
            'spa': 'Ayurveda & Wellness'
        }

        def score_item(item):
            s = 0
            cat = item.get('category', '').lower()
            for kw, target in keyword_category_map.items():
                if kw in q_lower and target.lower() == cat:
                    s += 1
            for act in item.get('activities', []):
                if act.lower() in q_lower:
                    s += 0.5
            return s

        ranked = sorted(tourism, key=score_item, reverse=True)

        response = intro
        for item in ranked[:4]:  # Show top 4
            name = item.get('name', 'Attraction')
            category = item.get('category', 'Attraction')
            province = item.get('province', '')
            district = item.get('district', '')
            description = item.get('description', '')[:80]
            activities = item.get('activities', [])[:2]
            rating = item.get('rating', 4.5)
            
            response += f"**{name}**\n"
            response += f"📍 {category} | {district}, {province}\n"
            response += f"⭐ Rating: {rating}/5\n"
            response += f"📝 {description}...\n"
            if activities:
                response += f"🎯 Activities: {', '.join(activities)}\n"
            response += "\n"
        
        response += "Want more details? Ask about specific attractions or activities!"
        return response
    
    def handle_general_query(self, message, results):
        """Handle general travel queries"""
        response = "That's a great question! Here's what I can help with:\n\n"
        response += "**Destinations** - Suggest places, attractions, weather\n"
        response += "**Routes** - Best ways to travel, transportation options\n"
        response += "**Guides** - Find experienced tour guides\n"
        response += "**Hotels** - Accommodation recommendations\n"
        response += "**Vehicles** - Book cars, buses, or other transport\n"
        response += "**Medical** - Find hospitals and emergency services\n"
        response += "**Trip Planning** - Create your perfect itinerary\n\n"
        response += f"Feel free to ask about any of these or anything specific about your trip!"
        
        return response
    
    def process_message(self, user_message):
        """Main method to process a message and return response"""

        # Store user message
        self.conversation_history.append({
            'role': 'user',
            'message': user_message
        })

        try:
            
            if self.context.get("pending_route"):
                response = self.handle_routes_query(user_message, {})

            else:
                # ================================
                # 2. Normal AI processing
                # ================================
                query_type = self.classify_query(user_message)

                # If message looks like a route request, force route handler
                route_keywords = ['to', 'from', 'route', 'how to go', 'direction', 'travel']
                if any(k in user_message.lower() for k in route_keywords):
                    response = self.handle_routes_query(user_message, {})
                else:
                    # Search knowledge base
                    search_results = self.search_knowledge_base(user_message)

                    # Generate response
                    response = self.generate_response(
                        user_message,
                        query_type,
                        search_results
                    )

        except Exception as e:
            print(f"chat_agent.process_message error: {e}")
            response = (
                "I encountered an internal error while processing your request. "
                "Please try rephrasing or ask about a different topic."
            )

        # Store assistant response
        self.conversation_history.append({
            'role': 'assistant',
            'message': response
        })

        return response

    def extract_locations(self, message):
        """
        Understand:
        how to go from A to B
        best route from A to B
        A to B
        from A to B via C
        """

        message = message.lower()

        # Remove common words
        message = re.sub(r'how to go|how to get|best route|route|way|travel|please', '', message)

        # via pattern
        via_match = re.search(r'from (.*?) to (.*?) via (.*)', message)
        if via_match:
            start = via_match.group(1).strip().title()
            end = via_match.group(2).strip().title()
            stops = [s.strip().title() for s in via_match.group(3).split(',')]
            return start, end, stops

        # from A to B
        match = re.search(r'from (.*?) to (.*)', message)
        if match:
            return match.group(1).strip().title(), match.group(2).strip().title(), []

        # A to B
        match = re.search(r'([a-zA-Z ]+) to ([a-zA-Z ]+)', message)
        if match:
            return match.group(1).strip().title(), match.group(2).strip().title(), []

        return None, None, []

# Global agent instance
chat_agent = TravelChatAgent()

def process_voice_message(self, audio_path):
    """
    Convert voice to text and process like normal message
    """

    try:
        text = transcribe_audio(audio_path)

        if not text:
            return "Sorry, I couldn't understand the audio."

        print("User said:", text)

        return self.process_message(text)

    except Exception as e:
        print("Speech error:", e)
        return "Voice processing failed."