from models.rag_model import search_all_knowledge, get_recommendations
from transformers import pipeline
import torch
import json
import re
from urllib.parse import quote_plus

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
        self.context = {}
    
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
        """Handle route/transportation queries"""
        routes = results.get('routes', [])
        vehicles = results.get('vehicles', [])
        
        response = "Here's transportation information for your journey:\n\n"
        
        if routes:
            response += "**Available Routes:**\n"
            for route in routes[:2]:
                response += f"• {route.get('description', 'Direct route')}\n"
        
        if vehicles:
            response += "\n**Transport Options:**\n"
            for vehicle in vehicles[:2]:
                vehicle_type = vehicle.get('type', 'Vehicle')
                fare = vehicle.get('estimated_fare', 'TBD')
                response += f"• {vehicle_type} - LKR {fare}\n"
        
        if not routes and not vehicles:
            return "I can help you plan your route! Please tell me where you're traveling from and where you want to go."
        
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
        # Store in history
        self.conversation_history.append({
            'role': 'user',
            'message': user_message
        })
        
        try:
            # Classify the query
            query_type = self.classify_query(user_message)

            # Search knowledge base
            search_results = self.search_knowledge_base(user_message)

            # Generate response
            response = self.generate_response(user_message, query_type, search_results)
        except Exception as e:
            # Fallback friendly message and log error
            print(f"chat_agent.process_message error: {e}")
            response = ("I encountered an internal error while processing your request. "
                        "Please try rephrasing or ask about a different topic.")
        
        # Store response in history
        self.conversation_history.append({
            'role': 'assistant',
            'message': response
        })
        
        return response


# Global agent instance
chat_agent = TravelChatAgent()